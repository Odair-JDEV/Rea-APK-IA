"""Agente interno do ReaDroid para gateways OpenAI-compatíveis.

Por que existe: quem usa gateway próprio não tem (e não precisa ter) o opencode
instalado. Este módulo implementa um ciclo de ferramentas pequeno e explícito,
falando direto com `POST /v1/chat/completions` do gateway, e só mexe dentro da
pasta do APK decodificado.

Limites de segurança:
- todo caminho é resolvido e precisa ficar dentro da pasta de trabalho;
- apktool.yml nunca é gravado (a reconstrução depende dele);
- leitura limitada por tamanho, busca limitada por número de linhas;
- o agente para sozinho depois de `max_steps` rodadas.

Dois modos de segurança, úteis para revisar antes de aceitar a edição:
- `read_only`: o modelo só lê; qualquer tentativa de gravar volta como erro.
- `dry_run`: as gravações viram propostas (caminho + conteúdo novo) e o arquivo no
  disco não muda. No fim, `run` devolve `proposals` para o chamador mostrar o diff.
"""

from __future__ import annotations

import difflib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

MAX_FILE_BYTES = 200_000
MAX_READ_CHARS = 40_000
MAX_SEARCH_HITS = 60
MAX_LIST_ENTRIES = 400
PROTECTED_FILES = {"apktool.yml"}
SESSIONS_DIRNAME = ".readroid_sessions"
SESSIONS_MAX = 10

SYSTEM_PROMPT = (
    "Você é um agente que edita arquivos de um APK decodificado pelo Apktool. "
    "Use as ferramentas para ler o AndroidManifest.xml e os arquivos relevantes antes de mudar algo. "
    "Faça a menor mudança possível, preserve a estrutura do projeto, não altere apktool.yml, "
    "não execute comandos e não tente acessar nada fora da pasta informada. "
    "Trabalhe em português nas explicações. Ao terminar, escreva um resumo curto do que mudou."
)

TOOLS: list[dict[str, Any]] = [
    {"type": "function", "function": {
        "name": "list_files",
        "description": "Lista arquivos e pastas dentro da pasta do APK decodificado.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Caminho relativo; '.' para a raiz."}}},
    }},
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Lê um arquivo de texto do projeto. Use em pedaços quando for grande.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Caminho relativo do arquivo."}},
            "required": ["path"]},
    }},
    {"type": "function", "function": {
        "name": "write_file",
        "description": ("Grava um arquivo de texto. Prefira editar arquivos existentes e manter "
                        "as mudanças pequenas. apktool.yml é protegido."),
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Caminho relativo do arquivo."},
            "content": {"type": "string", "description": "Conteúdo completo e final do arquivo."}},
            "required": ["path", "content"]},
    }},
    {"type": "function", "function": {
        "name": "search_text",
        "description": "Procura um texto literal nos arquivos do projeto e devolve arquivo e linha.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "Texto a procurar."},
            "path": {"type": "string", "description": "Pasta inicial; '.' para a raiz."}},
            "required": ["query"]},
    }},
]


class ToolError(Exception):
    """Erro devolvido ao modelo sem interromper o ciclo."""


def _resolve(workdir: Path, rel: str | None) -> Path:
    root = workdir.resolve()
    candidate = (root / (rel or ".")).resolve()
    if candidate != root and root not in candidate.parents:
        raise ToolError("Caminho fora da pasta do APK bloqueado.")
    return candidate


def _is_text(data: bytes) -> bool:
    return b"\x00" not in data[:8192]


def _read(workdir: Path, path: str) -> str:
    target = _resolve(workdir, path)
    if not target.is_file():
        raise ToolError(f"Arquivo não encontrado: {path}")
    size = target.stat().st_size
    if size > MAX_FILE_BYTES:
        raise ToolError(f"Arquivo grande demais ({size} bytes). Leia outro arquivo menor.")
    data = target.read_bytes()
    if not _is_text(data):
        raise ToolError("Arquivo binário; não é possível editar como texto.")
    text = data.decode("utf-8", errors="replace")
    if len(text) > MAX_READ_CHARS:
        return text[:MAX_READ_CHARS] + f"\n... (truncado; {len(text) - MAX_READ_CHARS} caracteres omitidos)"
    return text


def _write(workdir: Path, path: str, content: Any,
           read_only: bool = False, proposals: dict[str, str] | None = None) -> str:
    if not isinstance(content, str):
        raise ToolError("O conteúdo precisa ser texto.")
    target = _resolve(workdir, path)
    if target.name in PROTECTED_FILES:
        raise ToolError("apktool.yml é protegido; o ReaDroid precisa dele para reconstruir.")
    if target.is_dir():
        raise ToolError(f"{path} é uma pasta, não um arquivo.")
    rel = str(target.relative_to(workdir.resolve())).replace("\\", "/")
    if read_only:
        raise ToolError("Esta tarefa é somente leitura: não é permitido gravar arquivos.")
    if proposals is not None:
        proposals[rel] = content
        return f"Proposta registrada (não gravada ainda): {rel} ({len(content)} caracteres)."
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Gravado: {path} ({len(content)} caracteres)."


def _list(workdir: Path, path: str | None) -> str:
    root = _resolve(workdir, path)
    if not root.is_dir():
        raise ToolError(f"Pasta não encontrada: {path}")
    entries: list[str] = []
    for item in sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
        if item.name in {".git", "__pycache__"} or item.name == SESSIONS_DIRNAME:
            continue
        suffix = "/" if item.is_dir() else ""
        size = "" if item.is_dir() else f"  {item.stat().st_size} B"
        entries.append(f"{item.name}{suffix}{size}")
        if len(entries) >= MAX_LIST_ENTRIES:
            entries.append("... (limite de listagem atingido)")
            break
    base = root.relative_to(workdir.resolve()) if root != workdir.resolve() else Path(".")
    return f"{base}:\n" + ("\n".join(entries) if entries else "(vazio)")


def _search(workdir: Path, query: Any, path: str | None) -> str:
    needle = str(query or "")
    if not needle:
        raise ToolError("Informe o texto a procurar.")
    root = _resolve(workdir, path)
    hits: list[str] = []
    for item in root.rglob("*"):
        if len(hits) >= MAX_SEARCH_HITS:
            hits.append("... (resultados truncados)")
            break
        if not item.is_file() or item.name in PROTECTED_FILES:
            continue
        if SESSIONS_DIRNAME in item.relative_to(workdir.resolve()).parts:
            continue  # a IA não relê as próprias sessões salvas
        try:
            if item.stat().st_size > 1_000_000:
                continue
            data = item.read_bytes()
        except OSError:
            continue
        if not _is_text(data):
            continue
        for number, line in enumerate(data.decode("utf-8", errors="replace").splitlines(), 1):
            if needle in line:
                rel = item.relative_to(workdir.resolve())
                hits.append(f"{rel}:{number}: {line.strip()[:200]}")
                if len(hits) >= MAX_SEARCH_HITS:
                    break
    return "\n".join(hits) if hits else "Nenhuma ocorrência."


def execute(workdir: Path, name: str, args: dict[str, Any],
            read_only: bool = False, proposals: dict[str, str] | None = None) -> str:
    """Executa uma ferramenta e devolve texto para o modelo."""
    try:
        if name == "list_files":
            return _list(workdir, args.get("path"))
        if name == "read_file":
            return _read(workdir, str(args.get("path", "")))
        if name == "write_file":
            return _write(workdir, str(args.get("path", "")), args.get("content"),
                          read_only=read_only, proposals=proposals)
        if name == "search_text":
            return _search(workdir, args.get("query"), args.get("path"))
        return f"Ferramenta desconhecida: {name}"
    except (ToolError, OSError, ValueError) as exc:
        return f"Erro: {exc}"


def _activity(name: str, args: dict[str, Any]) -> str:
    if name in ("read_file", "write_file", "list_files"):
        return f"{name}: {args.get('path', '.')}"
    if name == "search_text":
        return f"search_text: {args.get('query', '')!r}"
    return name


def _session_dir(workdir: Path) -> Path:
    """Pasta de sessões desta pasta decodificada (fora do conteúdo do APK reconstruído)."""
    return workdir / SESSIONS_DIRNAME


def save_session(workdir: Path, messages: list[dict[str, Any]], steps_used: int) -> str | None:
    """Guarda a conversa do agente para retomada e devolve o ID (não o caminho).
    Nunca levanta; problema de disco devolve None e o fluxo segue sem retomada."""
    import time
    try:
        workdir = workdir.resolve()
        folder = _session_dir(workdir)
        folder.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        path = folder / f"session_{stamp}.json"
        suffix = 2  # duas sessões no mesmo segundo não podem se sobrescrever
        while path.exists():
            path = folder / f"session_{stamp}-{suffix}.json"
            suffix += 1
        path.write_text(json.dumps({"messages": messages, "steps_used": steps_used},
                                   ensure_ascii=False), encoding="utf-8")
        # limite de sessões guardadas: apaga as mais antigas
        sessions = sorted(folder.glob("session_*.json"))
        for old in sessions[:-SESSIONS_MAX]:
            old.unlink(missing_ok=True)
        return path.stem[len("session_"):]
    except OSError:
        return None


def load_session(workdir: Path, session_id: str) -> list[dict[str, Any]] | None:
    """Lê os `messages` de uma sessão salva. Retorna None se não existir ou estiver inválida."""
    try:
        workdir = workdir.resolve()
        path = (_session_dir(workdir) / f"session_{session_id}.json").resolve()
        root = workdir.resolve()
        if root not in path.parents and path.parent != root:
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        messages = data.get("messages")
        if not isinstance(messages, list) or not messages:
            return None
        return messages
    except (OSError, ValueError):
        return None


def list_sessions(workdir: Path) -> list[dict[str, str]]:
    """Sessões salvas desta pasta, da mais nova para a mais antiga."""
    out: list[dict[str, str]] = []
    try:
        folder = _session_dir(workdir.resolve())
        for path in sorted(folder.glob("session_*.json"), reverse=True):
            stem = path.stem[len("session_"):]
            out.append({"id": stem, "path": str(path)})
    except OSError:
        pass
    return out


def run(workdir: Path, instruction: str,
        request: Callable[[dict[str, Any]], Any],
        emit: Callable[[str], None] = print,
        animate: Callable[[str], Any] | None = None,
        max_steps: int = 60, read_only: bool = False,
        dry_run: bool = False,
        session_id: str | None = None) -> dict[str, Any]:
    """Ciclo de ferramentas: modelo pede leitura/edição, ReaDroid executa e devolve o resultado.

    `request(payload)` faz a chamada ao gateway e devolve o JSON já decodificado.
    `animate(label)` é um gerenciador de contexto que mostra que a IA está trabalhando.
    `read_only` bloqueia gravações; `dry_run` guarda as gravações como propostas.
    `session_id` retoma uma conversa salva por um `run` anterior que bateu no limite.
    """
    import contextlib

    workdir = workdir.resolve()
    system = SYSTEM_PROMPT
    if read_only:
        system += (" IMPORTANTE: nesta tarefa você NÃO pode alterar arquivos; apenas ler, "
                   "procurar e explicar. Não peça para gravar.")
    elif dry_run:
        system += (" IMPORTANTE: as gravações serão guardadas como propostas para o usuário "
                   "aprovar depois. Continue como se tivessem sido aplicadas.")
    if session_id:
        saved = load_session(workdir, session_id)
        if saved is None:
            return {"ok": False, "steps": 0, "message": "Sessão não encontrada ou inválida."}
        messages = list(saved)
        messages.append({"role": "user", "content":
                         "Você atingiu o limite de passos na tentativa anterior e esta é a "
                         "continuação. Retome de onde parou e termine a tarefa."})
    else:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": instruction},
        ]
    animate = animate or (lambda label: contextlib.nullcontext())
    proposals: dict[str, str] | None = {} if dry_run else None

    for step in range(1, max_steps + 1):
        payload = {"messages": messages, "tools": TOOLS, "tool_choice": "auto"}
        try:
            with animate(f"IA editando… (passo {step})"):
                data = request(payload)
        except Exception as exc:  # rede/HTTP: o chamador decide como reportar
            return {"ok": False, "steps": step, "message": _describe_error(exc)}

        if isinstance(data, dict) and data.get("error"):
            err = data["error"]
            text = err.get("message") if isinstance(err, dict) else err
            return {"ok": False, "steps": step, "message": str(text)[:300]}

        choices = data.get("choices") if isinstance(data, dict) else None
        message = (choices or [{}])[0].get("message") or {}
        calls = message.get("tool_calls") or []
        if not calls:
            text = (message.get("content") or "").strip()
            return {"ok": True, "steps": step,
                    "message": text or "A IA terminou sem enviar mensagem.",
                    "proposals": proposals or {}}

        messages.append({"role": "assistant", "content": message.get("content") or "",
                         "tool_calls": calls})
        for call in calls:
            function = call.get("function") or {}
            name = str(function.get("name") or "")
            raw = function.get("arguments") or "{}"
            try:
                args = json.loads(raw) if isinstance(raw, str) else dict(raw)
            except (ValueError, TypeError):
                args = {}
            if not isinstance(args, dict):
                args = {}
            emit("  · " + _activity(name, args))
            result = execute(workdir, name, args, read_only=read_only, proposals=proposals)
            messages.append({"role": "tool", "tool_call_id": call.get("id") or name,
                             "content": result})

    # Limite de passos: guarda a conversa inteira para o usuário poder retomar depois.
    saved_id = None
    if not session_id:  # sessão nova; retomadas já têm sessão própria
        saved_id = save_session(workdir, messages, max_steps)
    return {"ok": False, "steps": max_steps, "limit_reached": True,
            "session_id": saved_id,
            "proposals": proposals or {},
            "message": (f"A IA atingiu o limite de {max_steps} passos sem terminar. "
                        + ("Conversa salva; você pode retomar de onde parou. " if saved_id else "")
                        + "Aumente o limite em [L] no menu de IA ou peça uma tarefa menor.")}


def diff_proposal(workdir: Path, rel: str, new_text: str, context: int = 2) -> list[str]:
    """Diff unificado entre o arquivo atual e a proposta. Arquivo novo aparece como tudo '+'."""
    target = Path(workdir).resolve() / rel
    try:
        old = target.read_text(encoding="utf-8", errors="replace") if target.is_file() else ""
    except OSError:
        old = ""
    lines = list(difflib.unified_diff(
        old.splitlines(), new_text.splitlines(),
        fromfile=f"a/{rel}" if old else "/dev/null", tofile=f"b/{rel}", lineterm="", n=context))
    return lines[:400]


def summarize_proposals(workdir: Path, proposals: dict[str, str]) -> list[str]:
    """Resumo legível das propostas: cada arquivo com contagem de linhas +/-."""
    out: list[str] = []
    for rel in sorted(proposals):
        diff = diff_proposal(workdir, rel, proposals[rel])
        added = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
        removed = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))
        out.append(f"{rel}: +{added} / -{removed}")
    return out


def apply_proposals(workdir: Path, proposals: dict[str, str]) -> dict[str, Any]:
    """Grava as propostas aprovadas, respeitando os mesmos limites do agente."""
    written: list[str] = []
    problems: list[str] = []
    for rel, content in proposals.items():
        # execute() nunca levanta: erros voltam como texto começando com "Erro:".
        try:
            outcome = execute(workdir, "write_file", {"path": rel, "content": content})
        except Exception as exc:  # rede de segurança: nada aqui deveria levantar
            problems.append(f"{rel}: {exc}")
            continue
        if str(outcome).startswith("Erro:"):
            problems.append(f"{rel}: {outcome}")
        else:
            written.append(rel)
    return {"ok": not problems, "written": written, "problems": problems}


def _describe_error(exc: Exception) -> str:
    text = str(exc).strip() or exc.__class__.__name__
    if len(text) > 300:
        text = text[:300] + "…"
    return f"Falha ao falar com o gateway: {text}"
