"""Assistente de IA OPCIONAL do ReaDroid (OpenRouter+opencode OU Codex).

Regras deste módulo:
- O núcleo do ReaDroid nunca depende dele: o app.py só o importa quando você abre o menu 15,
  e se este arquivo for apagado o menu 15 simplesmente some.
- Usa só a biblioteca padrão. A chave do OpenRouter (provedor opencode) fica FORA do projeto
  (~/.readroid), com permissão 600, para nunca ir parar num commit do GitHub.
- Dois provedores de IA, escolhidos no menu (opção [P]):
    * opencode  -> ReaDroid gerencia a chave do OpenRouter e gera o opencode.json sozinho.
    * codex     -> usa o binário `codex` já configurado globalmente no seu Termux (o ReaDroid
                   não mexe em chave/modelo do Codex, só chama o binário na pasta certa).
- Os dois são sempre iniciados dentro de uma pasta de trabalho explícita (nunca na pasta
  pessoal). Era isso que fazia a IA "abrir mas não responder" fora da pasta certa.
"""
from __future__ import annotations

import getpass
import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from . import ui as _ui

HOME_DIR = Path(os.environ.get("READROID_HOME") or (Path.home() / ".readroid"))
KEY_FILE = HOME_DIR / "openrouter.key"
GATEWAY_KEY_FILE = HOME_DIR / "gateway.key"
OC_CONFIG = HOME_DIR / "opencode.json"
SETTINGS_FILE = HOME_DIR / "ai.json"
WORKSPACE = HOME_DIR / "workspace"

OPENROUTER_API = "https://openrouter.ai/api/v1"
# IDs gratuitos vistos no catálogo do OpenRouter em out/2026. Modelos :free saem do ar com
# frequência (o nano-30b deixou de ser gratuito), por isso o ReaDroid também troca sozinho.
DEFAULT_MODEL = "nvidia/nemotron-3.5-lightning:free"
PREFERRED_MODELS = (
    "nvidia/nemotron-3.5-lightning:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
)

PROVIDER_OPENCODE = "opencode"
PROVIDER_CODEX = "codex"
PROVIDER_GATEWAY = "gateway"
PROVIDERS = (PROVIDER_OPENCODE, PROVIDER_CODEX, PROVIDER_GATEWAY)
DEFAULT_PROVIDER = PROVIDER_OPENCODE

PROVIDER_LABELS = {
    PROVIDER_OPENCODE: "opencode (OpenRouter, gerenciado pelo ReaDroid)",
    PROVIDER_CODEX: "codex (binário global do seu Termux)",
    PROVIDER_GATEWAY: "opencode (gateway próprio, OpenAI-compatível)",
}

# Comando do Codex em modo automático: roda a tarefa sozinho, editando arquivos sem
# perguntar de volta. Ajustável em ai.json (chave "codex_exec_args") caso sua versão do
# codex use flags diferentes — o ReaDroid nunca sobrescreve se você já tiver configurado.
DEFAULT_CODEX_EXEC_ARGS = ["exec", "--full-auto", "--skip-git-repo-check"]

_CTRL_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]|[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_KEY_RE = re.compile(r"^[A-Za-z0-9_\-]{20,200}$")
_BAD_MODEL_WORDS = ("embed", "rerank", "guard", "safety", "-vl", "omni", "parse")
_UNAVAIL_RE = re.compile(r"unavailable for free|slug instead|no endpoints found|model.{0,30}(not found|not available)",
                         re.IGNORECASE)


def _clean(text: Any) -> str:
    """Remove escapes ANSI/controle: saída de IA e de rede é conteúdo não confiável."""
    return _CTRL_RE.sub("", str(text))


# ------------------------------------------------------------------ chave e configuração

def valid_key_format(key: str) -> bool:
    return bool(_KEY_RE.match(key))


def _write_private(path: Path, text: str) -> None:
    HOME_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(HOME_DIR, 0o700)
    except OSError:
        pass
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(text)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def save_key(key: str) -> None:
    """Grava a chave com permissão 600 (só você lê)."""
    _write_private(KEY_FILE, key.strip() + "\n")


def load_key() -> str | None:
    env = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if env:
        return env
    try:
        value = KEY_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return value or None


def _load_settings() -> dict[str, Any]:
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_settings(patch: dict[str, Any]) -> None:
    """Lê o ai.json, aplica só as chaves de patch e regrava (nunca apaga as outras)."""
    HOME_DIR.mkdir(parents=True, exist_ok=True)
    data = _load_settings()
    data.update(patch)
    SETTINGS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_model() -> str:
    if load_provider() == PROVIDER_GATEWAY:
        return load_gateway_config().get("model", "") or str(_load_settings().get("model", "")).strip()
    model = str(_load_settings().get("model", "")).strip()
    return model or DEFAULT_MODEL


def load_gateway_config() -> dict[str, str]:
    raw = _load_settings().get("gateway", {})
    if not isinstance(raw, dict):
        return {}
    return {key: str(value) for key, value in raw.items()
            if key in {"base_url", "auth_scheme", "model"} and value is not None}


def save_gateway_config(base_url: str, auth_scheme: str, model: str) -> None:
    _save_settings({"gateway": {"base_url": base_url.rstrip("/"),
                                 "auth_scheme": auth_scheme,
                                 "model": model}})


def load_gateway_key() -> str | None:
    env = os.environ.get("READROID_GATEWAY_API_KEY", "").strip()
    if env:
        return env
    try:
        value = GATEWAY_KEY_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return value or None


def save_gateway_key(key: str) -> None:
    _write_private(GATEWAY_KEY_FILE, key.strip() + "\n")


def valid_gateway_url(url: str) -> bool:
    return bool(re.fullmatch(r"https?://[^\s]+", url.strip(), re.IGNORECASE))


def gateway_api_url(base_url: str, endpoint: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/v1"):
        return base + endpoint
    return base + "/v1" + endpoint


def save_model(model: str) -> None:
    _save_settings({"model": model})


def test_gateway(base_url: str, key: str, model: str, auth_scheme: str = "bearer") -> dict[str, Any]:
    try:
        data = _request(gateway_api_url(base_url, "/chat/completions"), key,
                        {"model": model, "max_tokens": 64,
                         "messages": [{"role": "user", "content": "Responda apenas: OK"}]},
                        auth_scheme=auth_scheme)
        if isinstance(data, dict) and data.get("error"):
            return {"ok": False, "message": _clean(data["error"].get("message", data["error"]))[:200]}
        return {"ok": True, "message": "Chave e modelo do gateway funcionando."}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "message": explain_http_error(exc.code)}
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return {"ok": False, "message": f"Falha no gateway: {_clean(exc)[:100]}"}


def discover_gateway_models(base_url: str, key: str, auth_scheme: str = "bearer") -> list[str]:
    try:
        data = _request(gateway_api_url(base_url, "/models"), key, timeout=20, auth_scheme=auth_scheme)
        rows = data.get("data", []) if isinstance(data, dict) else []
        return sorted({str(row.get("id")) for row in rows if isinstance(row, dict) and row.get("id")})
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, AttributeError):
        return []


def gateway_chat(payload: dict[str, Any], timeout: int = 300) -> Any:
    """Chamada de chat no gateway configurado, com a autenticação escolhida."""
    cfg = load_gateway_config()
    key = load_gateway_key()
    if not cfg.get("base_url") or not key:
        raise ValueError("Gateway sem URL ou chave configurada.")
    body = {"model": load_model(), **payload}
    return _request(gateway_api_url(cfg["base_url"], "/chat/completions"), key, body,
                    timeout=timeout, auth_scheme=cfg.get("auth_scheme", "bearer"))


def gateway_agent_available() -> bool:
    """O agente interno só precisa de URL, chave e modelo — não precisa do opencode."""
    cfg = load_gateway_config()
    return bool(cfg.get("base_url") and cfg.get("model") and load_gateway_key())


class _Spinner:
    """Mostra que a IA está trabalhando enquanto a requisição está em andamento."""

    FRAMES = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")

    def __init__(self, label: str, stream=None):
        self.label = label
        self.stream = stream
        self._stop = None
        self._thread = None

    def __enter__(self):
        import sys
        import threading
        stream = self.stream or sys.stdout
        stop = threading.Event()
        self._stop = stop

        def loop():
            index = 0
            while not stop.is_set():
                frame = self.FRAMES[index % len(self.FRAMES)]
                try:
                    stream.write("\r  " + frame + " " + self.label + "   ")
                    stream.flush()
                except (OSError, ValueError):
                    return
                index += 1
                stop.wait(0.12)
            try:
                stream.write("\r" + " " * (len(self.label) + 8) + "\r")
                stream.flush()
            except (OSError, ValueError):
                pass

        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc):
        if self._stop is not None:
            self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1)
        return False


def _spinner(label: str):
    return _Spinner(label)


def run_gateway_agent(workdir: Path, instruction: str, emit=print, animate=None,
                      read_only: bool = False, dry_run: bool = False,
                      session_id: str | None = None) -> dict[str, Any]:
    """Edita a pasta decodificada usando o agente interno (sem opencode).

    `read_only` só permite leitura; `dry_run` guarda as gravações como propostas;
    `session_id` retoma uma sessão salva depois de o limite de passos ser atingido."""
    from . import agent
    if not gateway_agent_available():
        return {"ok": False, "message": "Gateway sem URL, chave ou modelo. Configure na opção [10]."}
    ok, why = safe_workdir(workdir)
    if not ok:
        return {"ok": False, "message": why}
    return agent.run(workdir, instruction, gateway_chat, emit=emit,
                     animate=animate or _spinner,
                     max_steps=load_agent_max_steps(),
                     read_only=read_only, dry_run=dry_run, session_id=session_id)


def load_provider() -> str:
    provider = str(_load_settings().get("provider", "")).strip()
    return provider if provider in PROVIDERS else DEFAULT_PROVIDER


def save_provider(provider: str) -> None:
    if provider not in PROVIDERS:
        raise ValueError(f"Provedor desconhecido: {provider}")
    _save_settings({"provider": provider})


def load_codex_bin() -> str:
    return str(_load_settings().get("codex_bin", "") or "codex").strip() or "codex"


def load_codex_exec_args() -> list[str]:
    args = _load_settings().get("codex_exec_args")
    return [str(a) for a in args] if isinstance(args, list) and args else list(DEFAULT_CODEX_EXEC_ARGS)


DEFAULT_AGENT_MAX_STEPS = 60
MIN_AGENT_MAX_STEPS = 5
MAX_AGENT_MAX_STEPS = 300


def load_agent_max_steps() -> int:
    """Limite de passos do agente interno (lido de ai.json, com limites de segurança)."""
    raw = _load_settings().get("agent_max_steps")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_AGENT_MAX_STEPS
    return max(MIN_AGENT_MAX_STEPS, min(MAX_AGENT_MAX_STEPS, value))


def save_agent_max_steps(steps: int) -> int:
    value = max(MIN_AGENT_MAX_STEPS, min(MAX_AGENT_MAX_STEPS, int(steps)))
    _save_settings({"agent_max_steps": value})
    return value


def build_opencode_config(model: str, provider: str | None = None) -> dict[str, Any]:
    """Gera a configuração efêmera do OpenCode sem inserir segredos no JSON."""
    provider = provider or load_provider()
    if provider == PROVIDER_GATEWAY:
        cfg = load_gateway_config()
        base_url = cfg.get("base_url", "").rstrip("/")
        if not base_url.endswith("/v1"):
            base_url += "/v1"
        auth_scheme = cfg.get("auth_scheme", "bearer")
        settings: dict[str, Any] = {
            "baseURL": base_url,
            "apiKey": "{env:READROID_GATEWAY_API_KEY}",
        }
        if auth_scheme == "x-api-key":
            settings["headers"] = {"x-api-key": "{env:READROID_GATEWAY_API_KEY}"}
        return {
            "$schema": "https://opencode.ai/config.json",
            "model": f"gateway/{model}",
            "small_model": f"gateway/{model}",
            "providers": {
                "gateway": {
                    "env": ["READROID_GATEWAY_API_KEY"],
                    "package": "@opencode/ai/providers/openai-compatible",
                    "settings": settings,
                    "models": {model: {"modelID": model}},
                }
            },
        }
    return {
        "$schema": "https://opencode.ai/config.json",
        "model": f"openrouter/{model}",
        "small_model": f"openrouter/{model}",
        "provider": {"openrouter": {"models": {model: {}}}},
    }


def write_opencode_config(model: str, provider: str | None = None) -> Path:
    HOME_DIR.mkdir(parents=True, exist_ok=True)
    OC_CONFIG.write_text(json.dumps(build_opencode_config(model, provider), indent=2) + "\n", encoding="utf-8")
    return OC_CONFIG


def configure(key: str, model: str | None = None, provider: str = PROVIDER_OPENCODE,
              base_url: str | None = None, auth_scheme: str = "bearer") -> dict[str, Any]:
    """Configura um provedor sem gravar segredos no arquivo do projeto.

    Para o provedor `gateway` a chave fica em ~/.readroid/gateway.key (0600) e a URL/auth
    vão para ~/.readroid/ai.json. O opencode recebe a configuração com {env:...}."""
    provider = provider or load_provider()
    key = key.strip()
    if provider == PROVIDER_GATEWAY:
        # Nunca herdar o modelo padrão do OpenRouter como modelo do gateway.
        model = (model or load_gateway_config().get("model", "")).strip()
    else:
        model = (model or load_model()).strip()
    if provider == PROVIDER_GATEWAY:
        if not base_url or not valid_gateway_url(base_url):
            return {"ok": False, "message": "Informe uma URL base válida, iniciando com http:// ou https://."}
        if not key.strip() or not model:
            return {"ok": False, "message": "Informe a chave e o ID do modelo do gateway."}
        if auth_scheme not in ("bearer", "x-api-key"):
            return {"ok": False, "message": "Autenticação deve ser bearer ou x-api-key."}
        save_gateway_key(key)
        save_gateway_config(base_url, auth_scheme, model)
        path = write_opencode_config(model, provider)
        WORKSPACE.mkdir(parents=True, exist_ok=True)
        return {"ok": True, "model": model, "config": str(path), "provider": provider,
                "message": f"Chave do gateway salva em {GATEWAY_KEY_FILE} (permissão 600) e opencode configurado."}
    if not valid_key_format(key):
        return {"ok": False, "message": "Isso não parece uma chave de API (sem espaços, 20+ caracteres)."}
    save_key(key)
    save_model(model)
    path = write_opencode_config(model)
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    return {"ok": True, "model": model, "config": str(path),
            "message": f"Chave salva em {KEY_FILE} (permissão 600) e opencode configurado."}


def disable() -> list[str]:
    """Apaga chaves, configs e preferências. O restante do ReaDroid não é afetado."""
    removed = []
    for path in (KEY_FILE, GATEWAY_KEY_FILE, OC_CONFIG, SETTINGS_FILE):
        try:
            path.unlink()
            removed.append(str(path))
        except FileNotFoundError:
            continue
        except OSError:
            continue
    return removed


# ------------------------------------------------------------------ opencode

def find_opencode() -> str | None:
    found = shutil.which("opencode")
    if found:
        return found
    candidate = Path.home() / ".opencode" / "bin" / "opencode"
    return str(candidate) if candidate.is_file() else None


def find_codex() -> str | None:
    """O Codex não é gerenciado pelo ReaDroid: usa o binário já configurado no Termux."""
    found = shutil.which(load_codex_bin())
    if found:
        return found
    candidate = Path.home() / ".codex" / "bin" / "codex"
    return str(candidate) if candidate.is_file() else None


def codex_command(binary: str, prompt: str | None = None) -> list[str]:
    """Sem prompt: abre a TUI interativa do Codex. Com prompt: `codex exec` em modo
    automático (--full-auto) — ele edita os arquivos sozinho, sem perguntar de volta."""
    if prompt is None:
        return [binary]
    return [binary, *load_codex_exec_args(), prompt]


def find_provider_binary(provider: str) -> str | None:
    return find_codex() if provider == PROVIDER_CODEX else find_opencode()


def safe_workdir(path: Path) -> tuple[bool, str]:
    """Recusa pastas enormes (HOME, raiz). Abrir o opencode na pasta pessoal faz ele
    tratar o Termux inteiro como projeto, e é uma das causas de travar sem responder."""
    resolved = path.resolve()
    if resolved in (Path.home().resolve(), Path("/"), Path("/data/data/com.termux/files")):
        return False, "Escolha a pasta de um APK (output/<app>_apktool), não a pasta pessoal."
    if not resolved.is_dir():
        return False, "Pasta não encontrada."
    return True, ""


def build_env(key: str, provider: str = PROVIDER_OPENCODE) -> dict[str, str]:
    env = os.environ.copy()
    env["OPENCODE_CONFIG"] = str(OC_CONFIG)
    if provider == PROVIDER_GATEWAY:
        env["READROID_GATEWAY_API_KEY"] = key
    else:
        env["OPENROUTER_API_KEY"] = key
    return env


def opencode_command(binary: str, model: str, prompt: str | None = None,
                     provider: str = PROVIDER_OPENCODE) -> list[str]:
    """Sem prompt: abre a interface interativa. Com prompt: `opencode run`."""
    model_ref = f"gateway/{model}" if provider == PROVIDER_GATEWAY else f"openrouter/{model}"
    if prompt is None:
        return [binary, "-m", model_ref]
    return [binary, "run", "-m", model_ref, prompt]


def _ready(provider: str) -> tuple[bool, str, str | None]:
    """Checa se o provedor está pronto para uso. Devolve (ok, mensagem_de_erro, binário)."""
    binary = find_provider_binary(provider)
    if provider == PROVIDER_GATEWAY:
        # O gateway usa o agente interno: opencode é opcional, não obrigatório.
        if not gateway_agent_available():
            return False, ("Gateway sem URL, chave ou modelo. Configure na opção [10] "
                           "(o opencode não é necessário)."), None
        return True, "", binary
    if provider == PROVIDER_OPENCODE:
        if not load_key():
            return False, "IA não configurada. Use a opção de configuração do provedor.", None
        if not binary:
            return False, "opencode não encontrado no PATH.", None
    elif not binary:
        return False, ("codex não encontrado no PATH. Confirme que `codex` funciona "
                       "direto no Termux fora do ReaDroid."), None
    return True, "", binary


def ready(provider: str | None = None) -> tuple[bool, str, str | None]:
    """API pública de prontidão, usada pelo assistente guiado."""
    return _ready(provider or load_provider())


def _command_for(provider: str, binary: str, prompt: str | None) -> list[str]:
    if provider in (PROVIDER_OPENCODE, PROVIDER_GATEWAY):
        return opencode_command(binary, load_model(), prompt, provider)
    return codex_command(binary, prompt)


def _env_for(provider: str) -> dict[str, str]:
    if provider in (PROVIDER_OPENCODE, PROVIDER_GATEWAY):
        key = load_gateway_key() if provider == PROVIDER_GATEWAY else load_key()
        return build_env(key, provider) if key else os.environ.copy()
    # Codex usa a configuração global já existente no Termux: herda o ambiente como está.
    return os.environ.copy()


def open_interactive(workdir: Path) -> dict[str, Any]:
    provider = load_provider()
    if provider == PROVIDER_GATEWAY:
        return {"ok": False, "message": ("O gateway usa o agente interno e não tem tela interativa. "
                                         "Use [4] Editar com a IA e reconstruir.")}
    ready, why, binary = _ready(provider)
    if not ready:
        return {"ok": False, "message": why}
    ok, why = safe_workdir(workdir)
    if not ok:
        return {"ok": False, "message": why}
    if provider in (PROVIDER_OPENCODE, PROVIDER_GATEWAY):
        write_opencode_config(load_model(), provider)
    label = PROVIDER_LABELS[provider]
    try:
        code = subprocess.run(_command_for(provider, binary, None), cwd=workdir, env=_env_for(provider),
                              check=False).returncode
    except OSError as exc:
        return {"ok": False, "message": f"Não foi possível iniciar o {provider}: {exc}"}
    return {"ok": True, "message": f"{label} encerrado (código {code})."}


def ask_once(workdir: Path, prompt: str, timeout: int = 300, emit=print) -> dict[str, Any]:
    """Faz uma pergunta/tarefa no provedor ativo e imprime a saída linha a linha, já
    sanitizada. No provedor codex isto roda `codex exec --full-auto`: a IA edita os
    arquivos sozinha, sem pausar para confirmar cada passo."""
    provider = load_provider()
    if provider == PROVIDER_GATEWAY:
        return run_gateway_agent(workdir, prompt, emit=emit)
    ready, why, binary = _ready(provider)
    if not ready:
        return {"ok": False, "message": why}
    ok, why = safe_workdir(workdir)
    if not ok:
        return {"ok": False, "message": why}
    if provider == PROVIDER_OPENCODE:
        write_opencode_config(load_model(), provider)
    import threading
    try:
        proc = subprocess.Popen(_command_for(provider, binary, prompt), cwd=workdir, env=_env_for(provider),
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                errors="replace", stdin=subprocess.DEVNULL)
    except OSError as exc:
        return {"ok": False, "message": f"Não foi possível iniciar o {provider}: {exc}"}
    timer = threading.Timer(timeout, proc.kill)
    timer.start()
    lines = 0
    unavailable = False
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            text = _clean(line.rstrip("\n"))
            if provider in (PROVIDER_OPENCODE, PROVIDER_GATEWAY) and _UNAVAIL_RE.search(text):
                unavailable = True
            emit(text)
            lines += 1
        proc.wait()
    except KeyboardInterrupt:
        proc.kill()
        return {"ok": False, "message": "Interrompido."}
    finally:
        timer.cancel()
    if unavailable:
        return {"ok": False, "model_unavailable": True,
                "message": "O modelo escolhido não está disponível no provedor selecionado."}
    if proc.returncode in (-9, 137):
        return {"ok": False, "message": f"Sem resposta em {timeout}s; processo encerrado."}
    return {"ok": proc.returncode == 0 and lines > 0,
            "message": "Concluído." if proc.returncode == 0 and lines else f"O {provider} não devolveu resposta."}


# ------------------------------------------------------------------ OpenRouter direto (diagnóstico)

def _request(url: str, key: str | None = None, payload: dict | None = None, timeout: int = 45,
             auth_scheme: str = "bearer") -> Any:
    headers = {"Content-Type": "application/json", "User-Agent": "ReaDroid"}
    if key:
        if auth_scheme == "x-api-key":
            headers["x-api-key"] = key
        else:
            headers["Authorization"] = f"Bearer {key}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def explain_http_error(code: int) -> str:
    return {
        401: "Chave recusada pelo OpenRouter (inválida, apagada ou com erro de digitação).",
        402: "Conta sem crédito para este modelo. Escolha um modelo :free.",
        404: "Modelo indisponível no OpenRouter. Use 'trocar modelo' para escolher outro :free.",
        408: "Tempo esgotado no OpenRouter. Tente de novo.",
        429: "Limite do plano gratuito atingido. Espere alguns minutos ou troque de modelo.",
    }.get(code, f"O OpenRouter respondeu com erro HTTP {code}.")


def test_api(key: str, model: str) -> dict[str, Any]:
    """Testa chave + modelo direto na API, sem opencode. Separa 'problema de chave/modelo'
    de 'problema do opencode'."""
    payload = {"model": model, "max_tokens": 64,
               "messages": [{"role": "user", "content": "Responda apenas: OK"}]}
    try:
        data = _request(f"{OPENROUTER_API}/chat/completions", key, payload)
    except urllib.error.HTTPError as exc:
        return {"ok": False, "model_unavailable": exc.code in (400, 404),
                "message": explain_http_error(exc.code)}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"ok": False, "message": f"Sem conexão com o OpenRouter ({_clean(exc)[:80]})."}
    except ValueError:
        return {"ok": False, "message": "Resposta inesperada do OpenRouter."}
    if isinstance(data, dict) and data.get("error"):
        err = data["error"]
        msg = err.get("message") if isinstance(err, dict) else err
        return {"ok": False, "model_unavailable": bool(_UNAVAIL_RE.search(str(msg))),
                "message": _clean(msg)[:200] or "Erro devolvido pelo OpenRouter."}
    return {"ok": True, "message": "Chave e modelo funcionando."}


def pick_free_models(models: list[dict]) -> list[str]:
    """Filtra, do catálogo, modelos de chat Nemotron gratuitos."""
    found = []
    for item in models:
        mid = str(item.get("id", ""))
        low = mid.lower()
        if "nemotron" in low and mid.endswith(":free") and not any(w in low for w in _BAD_MODEL_WORDS):
            found.append(mid)
    rank = {m: i for i, m in enumerate(PREFERRED_MODELS)}
    return sorted(found, key=lambda m: (rank.get(m, len(rank)), m))


def list_free_nemotron() -> list[str]:
    try:
        data = _request(f"{OPENROUTER_API}/models", timeout=20)
        return pick_free_models(data.get("data", []))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, AttributeError):
        return []


def ensure_working_model(key: str, tried: tuple[str, ...] = (), max_tests: int = 4) -> str | None:
    """Procura um modelo Nemotron :free que responda, salva e reescreve a config.
    Só considera IDs terminados em :free: nunca troca para a versão paga sem você saber."""
    candidates = list(PREFERRED_MODELS)
    for mid in list_free_nemotron():
        if mid not in candidates:
            candidates.append(mid)
    skip = set(tried) | {load_model()}
    tests = 0
    for mid in candidates:
        if mid in skip or tests >= max_tests:
            continue
        tests += 1
        if test_api(key, mid)["ok"]:
            save_model(mid)
            write_opencode_config(mid)
            return mid
    return None


# ------------------------------------------------------------------ menu

PRIVACY = ("Modelos gratuitos podem registrar os prompts. Tudo o que a IA ler (código, strings,\n"
           "manifesto) é enviado pela internet. Use só em APK seu ou autorizado.")

PROMPT_SUMMARY = ("Você está numa pasta de um APK decodificado (apktool ou jadx). Leia o "
                  "AndroidManifest.xml e a estrutura de pastas e faça um resumo curto em português: "
                  "o que o app faz, permissões relevantes, componentes expostos e pontos que merecem "
                  "revisão manual. Não modifique nenhum arquivo.")
PROMPT_BUILD = ("Esta pasta é um APK decodificado pelo apktool e a reconstrução falhou com o erro abaixo. "
                "Explique a causa provável, aponte o arquivo e a linha e sugira a correção mínima. "
                "Não modifique nenhum arquivo, só explique.\n\nERRO:\n")


def ask_with_fallback(ui, folder: Path, prompt: str) -> dict[str, Any]:
    """ask_once; se o modelo gratuito saiu do ar (só acontece no opencode), troca por
    outro :free e tenta uma vez de novo."""
    res = ask_once(folder, prompt, emit=print)
    if res.get("model_unavailable") and load_provider() == PROVIDER_OPENCODE:
        key = load_key()
        print(ui.YELLOW + "Modelo gratuito indisponível. Procurando outro…" + ui.RESET)
        found = ensure_working_model(key, (load_model(),)) if key else None
        if found:
            print(ui.GREEN + f"Modelo trocado para openrouter/{found}. Tentando de novo…" + ui.RESET)
            res = ask_once(folder, prompt, emit=print)
        else:
            res["message"] += " Use [8] Trocar modelo para escolher outro."
    return res


def _choose_dir(ui) -> Path | None:
    outputs: Path = ui.OUTPUTS
    outputs.mkdir(parents=True, exist_ok=True)
    cands = sorted((p for p in outputs.iterdir()
                    if p.is_dir() and (p.name.endswith("_apktool") or p.name.endswith("_jadx"))),
                   key=lambda p: p.stat().st_mtime, reverse=True)[:15]
    if cands:
        print(ui.CYAN + "Pastas disponíveis:" + ui.RESET)
        for i, item in enumerate(cands, 1):
            print(f" [{i}] {ui.sanitize(item.name)}")
        print(" [P] Informar outro caminho")
        choice = ui.safe_input("Escolha a pasta: ").strip()
        if choice.lower() != "p":
            try:
                return cands[int(choice) - 1]
            except (ValueError, IndexError):
                print(ui.YELLOW + "Seleção não reconhecida." + ui.RESET)
    raw = ui.safe_input("Caminho da pasta do APK decodificado: ").strip().strip('"').strip("'")
    if not raw:
        return None
    path = Path(raw).expanduser()
    return path if path.is_dir() else None


def _paste_key(ui, label: str = "chave do OpenRouter") -> str:
    print(ui.DIM + f"Cole a {label} (a colagem não aparece na tela) e dê ENTER." + ui.RESET)
    try:
        return getpass.getpass("API key: ").strip()
    except (EOFError, KeyboardInterrupt, OSError):
        return ui.safe_input("API key: ").strip()


def _setup(ui, provider: str | None = None) -> bool:
    provider = provider or load_provider()
    if provider == PROVIDER_GATEWAY:
        cfg = load_gateway_config()
        base_url = ui.safe_input(f"URL base do gateway [{cfg.get('base_url', '')}]: ").strip() or cfg.get("base_url", "")
        if not valid_gateway_url(base_url):
            print(ui.RED + "URL inválida. Use http:// ou https://." + ui.RESET)
            return False
        auth_scheme = "x-api-key" if ui.safe_input("Autenticação: [1] Bearer, [2] x-api-key (padrão 1): ").strip() == "2" else "bearer"
        key = _paste_key(ui, "chave do gateway")
        if not key:
            print(ui.YELLOW + "Nada informado." + ui.RESET)
            return False
        model = ui.safe_input(f"ID do modelo [{cfg.get('model', '')}]: ").strip() or cfg.get("model", "")
        if not model:
            models = discover_gateway_models(base_url, key, auth_scheme)
            for i, item in enumerate(models[:20], 1):
                print(f" [{i}] {ui.sanitize(item)}")
            raw = ui.safe_input("ID do modelo: ").strip()
            model = models[int(raw) - 1] if raw.isdigit() and 1 <= int(raw) <= len(models) else raw
        result = configure(key, model, PROVIDER_GATEWAY, base_url, auth_scheme)
        if not result["ok"]:
            print(ui.RED + result["message"] + ui.RESET)
            return False
        save_provider(PROVIDER_GATEWAY)
        print(ui.GREEN + result["message"] + ui.RESET)
        diagnostic = test_gateway(base_url, key, model, auth_scheme)
        print(f" [{ui.GREEN + 'OK' if diagnostic['ok'] else ui.RED + 'falhou'}{ui.RESET}] Gateway: {diagnostic['message']}")
        return _run_checks(ui) if diagnostic["ok"] else False

    key = _paste_key(ui)
    if not key:
        print(ui.YELLOW + "Nada informado." + ui.RESET)
        return False
    result = configure(key, provider=PROVIDER_OPENCODE)
    if not result["ok"]:
        print(ui.RED + result["message"] + ui.RESET)
        return False
    save_provider(PROVIDER_OPENCODE)
    print(ui.GREEN + result["message"] + ui.RESET)
    print(f" Modelo: openrouter/{result['model']}")
    return _run_checks(ui)

def _run_checks_codex(ui) -> bool:
    print(ui.CYAN + "\nTestando (codex)…" + ui.RESET)
    binary = find_codex()
    print(f" [{ui.GREEN + 'OK' + ui.RESET if binary else ui.RED + 'falhou' + ui.RESET}] "
          f"codex: {binary or 'não encontrado no PATH'}")
    if not binary:
        return False
    print(ui.DIM + " Testando `codex exec` numa pasta neutra (até 2 min)… "
          "se sua versão usa outras flags, ajuste em ~/.readroid/ai.json (\"codex_exec_args\")." + ui.RESET)
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    out: list[str] = []
    res = ask_once(WORKSPACE, "Responda apenas: OK. Não edite nenhum arquivo.", timeout=120, emit=out.append)
    print(f" [{ui.GREEN + 'OK' + ui.RESET if res['ok'] else ui.RED + 'falhou' + ui.RESET}] "
          f"codex exec: {res['message']}")
    if out:
        print(ui.DIM + "   " + " | ".join(out)[-160:] + ui.RESET)
    return bool(res["ok"])


def _run_checks(ui) -> bool:
    provider = load_provider()
    if provider == PROVIDER_CODEX:
        return _run_checks_codex(ui)
    if provider == PROVIDER_GATEWAY:
        cfg, key, model = load_gateway_config(), load_gateway_key(), load_model()
        if not cfg.get("base_url") or not key:
            print(ui.YELLOW + "Configure primeiro URL e chave do gateway (opção [10])." + ui.RESET)
            return False
        api = test_gateway(cfg["base_url"], key, model, cfg.get("auth_scheme", "bearer"))
        print(f" [{ui.GREEN + 'OK' if api['ok'] else ui.RED + 'falhou'}{ui.RESET}] Gateway direto: {api['message']}")
        if not api["ok"]:
            return False
        binary = find_opencode()
        print(f" [{ui.GREEN + 'OK' if binary else ui.YELLOW + '--'}{ui.RESET}] opencode: "
              f"{binary or 'não instalado (opcional no gateway; o agente interno é usado)'}")
        WORKSPACE.mkdir(parents=True, exist_ok=True)
        out: list[str] = []
        result = run_gateway_agent(WORKSPACE, "Responda apenas: OK. Não edite nenhum arquivo.",
                                   emit=out.append)
        print(f" [{ui.GREEN + 'OK' if result['ok'] else ui.RED + 'falhou'}{ui.RESET}] Agente interno: {result['message']}")
        if out:
            print(ui.DIM + "   " + " | ".join(out)[-160:] + ui.RESET)
        return bool(result["ok"])
    key, model = load_key(), load_model()
    if not key:
        print(ui.YELLOW + "Sem chave configurada." + ui.RESET)
        return False
    print(ui.CYAN + "\nTestando (opencode)…" + ui.RESET)
    api = test_api(key, model)
    if not api["ok"] and api.get("model_unavailable"):
        print(ui.YELLOW + f" Modelo {model} indisponível. Procurando outro gratuito…" + ui.RESET)
        found = ensure_working_model(key, (model,))
        if found:
            model = found
            api = {"ok": True, "message": f"Chave e modelo funcionando (trocado para {found})."}
    print(f" [{ui.GREEN + 'OK' if api['ok'] else ui.RED + 'falhou'}{ui.RESET}] OpenRouter direto: {api['message']}")
    binary = find_opencode()
    print(f" [{ui.GREEN + 'OK' if binary else ui.YELLOW + '--'}{ui.RESET}] opencode: {binary or 'não encontrado (instale o opencode para usar IA)'}")
    if api["ok"] and binary:
        WORKSPACE.mkdir(parents=True, exist_ok=True)
        write_opencode_config(model)
        out: list[str] = []
        result = ask_once(WORKSPACE, "Responda apenas: OK", timeout=120, emit=out.append)
        print(f" [{ui.GREEN + 'OK' if result['ok'] else ui.RED + 'falhou'}{ui.RESET}] opencode: {result['message']}")
        return bool(result["ok"])
    return bool(api["ok"])


def _change_agent_limit(ui) -> None:
    current = load_agent_max_steps()
    print(ui.CYAN + "\nLimite de passos do agente interno" + ui.RESET)
    print(f"Atual: {current} passos")
    print(ui.DIM + f"Vale de {MIN_AGENT_MAX_STEPS} a {MAX_AGENT_MAX_STEPS}. Cada passo é uma rodada de "
          "ferramentas (ler, gravar, buscar) ou a resposta final." + ui.RESET)
    raw = ui.safe_input(f"Novo limite [{current}] (ENTER para manter): ").strip()
    if not raw:
        return
    if not raw.isdigit():
        print(ui.YELLOW + "Informe um número." + ui.RESET)
        return
    value = save_agent_max_steps(int(raw))
    if value != int(raw):
        print(ui.YELLOW + f"Ajustado para {value} (limite permitido)." + ui.RESET)
    print(ui.GREEN + f"Limite definido: {value} passos." + ui.RESET)


def _change_model(ui) -> None:
    provider = load_provider()
    if provider == PROVIDER_CODEX:
        print(ui.YELLOW + "O modelo do Codex é gerenciado pela configuração global do Codex." + ui.RESET)
        return
    if provider == PROVIDER_GATEWAY:
        cfg = load_gateway_config()
        models = discover_gateway_models(cfg.get("base_url", ""), load_gateway_key() or "",
                                         cfg.get("auth_scheme", "bearer"))
        print(ui.DIM + "Modelos anunciados pelo gateway:" + ui.RESET)
    else:
        models = list_free_nemotron()
        print(ui.DIM + "Buscando modelos Nemotron gratuitos…" + ui.RESET)
    if not models:
        print(ui.YELLOW + "Não consegui listar. Você pode digitar o ID manualmente." + ui.RESET)
    for i, mid in enumerate(models[:20], 1):
        print(f" [{i}] {ui.sanitize(mid)}")
    raw = ui.safe_input("Número, ID completo, ou ENTER para cancelar: ").strip()
    if not raw:
        return
    chosen = models[int(raw) - 1] if raw.isdigit() and 1 <= int(raw) <= len(models) else raw
    if not chosen or any(c.isspace() for c in chosen):
        print(ui.RED + "ID de modelo inválido." + ui.RESET)
        return
    if provider == PROVIDER_GATEWAY:
        cfg = load_gateway_config()
        save_gateway_config(cfg.get("base_url", ""), cfg.get("auth_scheme", "bearer"), chosen)
        write_opencode_config(chosen, provider)
        label = "gateway"
    else:
        save_model(chosen)
        write_opencode_config(chosen)
        label = "openrouter"
    print(ui.GREEN + f"Modelo definido: {label}/{chosen}" + ui.RESET)


# ------------------------------------------------------------------ relatórios e ciclo editar -> reconstruir

MAX_ROUNDS = 3
PROMPT_CROSS = ("Abaixo está o resultado da análise estática do ReaDroid para este APK (JSON resumido). "
                "Para cada URL, domínio, IP e permissão sensível, procure no código desta pasta onde é usado "
                "e avalie o risco. Responda em português, de forma curta e organizada. "
                "Não modifique nenhum arquivo.\n\nRELATÓRIOS:\n")
EDIT_RULES = ("Regras: edite SOMENTE arquivos dentro desta pasta; não altere apktool.yml; faça a menor "
              "mudança possível; não rode comandos de build (o ReaDroid reconstrói depois); ao final, liste "
              "os arquivos que alterou.\n\n")
RECREATE_RULES = ("Regras: trabalhe SOMENTE dentro desta pasta (saída do apktool/jadx); não altere "
                   "apktool.yml; não rode comandos de build (o ReaDroid reconstrói depois); faça as "
                   "mudanças em etapas pequenas e coerentes, sem quebrar o resto do app; ao final, liste "
                   "os arquivos que criou ou alterou e um resumo do que foi recriado.\n\n")
PROMPT_RECREATE = ("Esta pasta é um app Android decodificado (apktool/jadx). Primeiro leia o "
                    "AndroidManifest.xml e entenda a estrutura geral. Depois, recrie/reescreva a parte "
                    "pedida abaixo com código limpo e moderno, preservando o comportamento observável "
                    "(mesmas telas, mesmo fluxo, mesmos nomes de recursos usados pelo manifesto), a menos "
                    "que a instrução peça explicitamente para mudar o comportamento. Use só em um app seu "
                    "ou que você tem autorização para modificar.\n\nO QUE RECRIAR:\n")


def _shrink(obj: Any, max_items: int = 40, max_str: int = 200) -> Any:
    """Reduz um JSON de relatório para caber num prompt (listas e textos longos cortados)."""
    if isinstance(obj, dict):
        return {k: _shrink(v, max_items, max_str) for k, v in obj.items()}
    if isinstance(obj, list):
        out = [_shrink(v, max_items, max_str) for v in obj[:max_items]]
        if len(obj) > max_items:
            out.append(f"... (+{len(obj) - max_items} itens omitidos)")
        return out
    if isinstance(obj, str) and len(obj) > max_str:
        return obj[:max_str] + "..."
    return obj


def find_reports(reports_dir: Path, decoded: Path) -> list[Path]:
    """Relatório mais recente de cada tipo para o APK desta pasta (nome: <apk>_<tipo>_<data>.json)."""
    stem = re.sub(r"_(apktool|jadx)$", "", decoded.name)
    latest: dict[str, Path] = {}
    try:
        files = sorted(reports_dir.glob(f"{stem}_*.json"), key=lambda p: p.stat().st_mtime)
    except OSError:
        return []
    for path in files:
        kind = path.name[len(stem) + 1:].rsplit("_", 2)[0]
        latest[kind] = path  # os mais novos vêm por último e sobrescrevem
    return list(latest.values())


def build_report_context(reports_dir: Path, decoded: Path, limit: int = 6000) -> str:
    chunks = []
    for path in find_reports(reports_dir, decoded):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        chunks.append(f"## {path.name}\n" + json.dumps(_shrink(data), ensure_ascii=False))
    return "\n\n".join(chunks)[:limit]


def snapshot(root: Path) -> dict[str, tuple[int, int]]:
    snap: dict[str, tuple[int, int]] = {}
    for item in root.rglob("*"):
        try:
            if item.is_file():
                st = item.stat()
                snap[str(item.relative_to(root))] = (st.st_size, st.st_mtime_ns)
        except OSError:
            continue
    return snap


def diff_snapshots(before: dict, after: dict) -> dict[str, list[str]]:
    return {"changed": sorted(k for k in after if k in before and before[k] != after[k]),
            "added": sorted(k for k in after if k not in before),
            "removed": sorted(k for k in before if k not in after)}


def build_error_text(result: dict[str, Any]) -> str:
    steps = result.get("steps", {})
    for name in ("quick_edits", "rebuild", "align", "keystore", "sign", "verify"):
        step = steps.get(name)
        if step and not step.get("ok") and not step.get("skipped"):
            return (f"Etapa: {name}\n{step.get('message', '')}\n"
                    f"{str(step.get('stderr', ''))[-3000:]}\n{str(step.get('stdout', ''))[-1000:]}").strip()
    return str(result.get("message", "Falha desconhecida na reconstrução."))


def fix_loop(decoded: Path, instruction: str, build_fn, ask_fn, confirm_fn, say,
             max_rounds: int = MAX_ROUNDS, rules: str = EDIT_RULES) -> dict[str, Any]:
    """Ciclo: (IA edita) -> reconstrói -> se falhar, devolve o erro à IA -> reconstrói de novo.

    build_fn() -> resultado do build_pipeline; ask_fn(prompt) -> {"ok":..,"message":..};
    confirm_fn(texto) -> bool; say(texto) imprime; rules -> cabeçalho de regras prefixado em
    cada chamada (EDIT_RULES para edição pontual, RECREATE_RULES para recriação). Tudo
    injetado para ser testável."""
    def report_changes(before):
        d = diff_snapshots(before, snapshot(decoded))
        n = sum(len(v) for v in d.values())
        say(f"Arquivos mexidos pela IA: {n} (alterados {len(d['changed'])}, novos {len(d['added'])}, "
            f"removidos {len(d['removed'])})")
        for name in (d["changed"] + d["added"] + d["removed"])[:15]:
            say("   " + name)

    if instruction:
        before = snapshot(decoded)
        res = ask_fn(rules + f"Pasta: {decoded}\nTarefa: {instruction}")
        if not res.get("ok"):
            return {"ok": False, "rounds": 0, "message": res.get("message", "A IA não respondeu.")}
        report_changes(before)
    last: dict[str, Any] = {}
    for rnd in range(1, max_rounds + 1):
        say(f"Reconstruindo (tentativa {rnd}/{max_rounds})…")
        last = build_fn()
        if last.get("ok"):
            return {"ok": True, "rounds": rnd, "result": last, "message": "APK reconstruído."}
        error = build_error_text(last)
        say("Falhou:\n" + error[-600:])
        if rnd == max_rounds or not confirm_fn("Pedir para a IA corrigir e tentar de novo?"):
            break
        before = snapshot(decoded)
        res = ask_fn(rules + f"Pasta: {decoded}\nA reconstrução falhou com este erro. Corrija a causa:\n{error}")
        if not res.get("ok"):
            return {"ok": False, "rounds": rnd, "result": last, "message": res.get("message", "A IA não respondeu.")}
        report_changes(before)
    return {"ok": False, "rounds": rnd if last else 0, "result": last, "message": "Não foi possível reconstruir."}


def _print_build(ui, result: dict[str, Any]) -> None:
    for name, label in (("quick_edits", "Edições"), ("rebuild", "Reconstrução"), ("align", "Alinhamento"),
                        ("keystore", "Chave"), ("sign", "Assinatura"), ("verify", "Verificação")):
        step = result.get("steps", {}).get(name)
        if step:
            mark = (ui.GREEN + "OK" if step.get("ok") else ui.YELLOW + "pulado" if step.get("skipped")
                    else ui.RED + "falhou") + ui.RESET
            print(f" [{mark}] {label}")


def _backup(ui, decoded: Path) -> Path | None:
    dest = ui.BUILDS / f"_backup_{decoded.name}_{__import__('datetime').datetime.now():%Y%m%d_%H%M%S}"
    try:
        shutil.copytree(decoded, dest)
        return dest
    except (OSError, shutil.Error):
        return None


def list_backups(builds_dir: Path, decoded: Path) -> list[Path]:
    """Backups desta pasta, do mais novo para o mais antigo."""
    try:
        found = [p for p in builds_dir.glob(f"_backup_{decoded.name}_*") if p.is_dir()]
    except OSError:
        return []
    return sorted(found, key=lambda p: p.stat().st_mtime, reverse=True)


def restore_backup(backup: Path, decoded: Path) -> dict[str, Any]:
    """Substitui a pasta decodificada pelo conteúdo do backup (com cópia de segurança do estado atual)."""
    if not backup.is_dir():
        return {"ok": False, "message": "Backup não encontrado."}
    safety = decoded.parent / f"{decoded.name}_antes_de_restaurar"
    try:
        if safety.exists():
            shutil.rmtree(safety)
        if decoded.exists():
            shutil.copytree(decoded, safety)
            shutil.rmtree(decoded)
        shutil.copytree(backup, decoded)
    except (OSError, shutil.Error) as exc:
        return {"ok": False, "message": f"Falha ao restaurar: {exc}"}
    return {"ok": True, "message": f"Restaurado de {backup.name}. Estado anterior em {safety.name}."}


def _backup_menu(ui, decoded: Path) -> None:
    """Opção dedicada: criar, listar e restaurar backups da pasta decodificada."""
    print(ui.CYAN + "\nBackup da pasta decodificada" + ui.RESET)
    print(f"Pasta: {decoded}")
    backups = list_backups(ui.BUILDS, decoded)
    if backups:
        print("Backups existentes (mais novo primeiro):")
        for i, item in enumerate(backups[:10], 1):
            print(f" [{i}] {ui.sanitize(item.name)}")
    else:
        print(ui.DIM + "Nenhum backup ainda para esta pasta." + ui.RESET)
    print(" [C] Criar backup agora")
    if backups:
        print(" [R] Restaurar um backup")
    choice = ui.safe_input("Escolha: ").strip().lower()
    if choice == "c":
        dest = _backup(ui, decoded)
        if dest is None:
            print(ui.RED + "Não foi possível criar o backup (espaço em disco?)." + ui.RESET)
        else:
            print(ui.GREEN + f"Backup criado: {dest}" + ui.RESET)
        return
    if choice == "r" and backups:
        raw = ui.safe_input("Número do backup a restaurar: ").strip()
        if not raw.isdigit() or not 1 <= int(raw) <= min(len(backups), 10):
            print(ui.YELLOW + "Seleção inválida." + ui.RESET)
            return
        target = backups[int(raw) - 1]
        print(ui.YELLOW + f"Isso substitui {decoded} pelo conteúdo de {target.name}." + ui.RESET)
        if ui.safe_input("Confirmar restauração? (s/N): ").strip().lower() != "s":
            return
        result = restore_backup(target, decoded)
        print((ui.GREEN if result["ok"] else ui.RED) + result["message"] + ui.RESET)
        return
    print(ui.DIM + "Nada alterado." + ui.RESET)


def _choose_ready_prompt(ui) -> dict[str, Any] | None:
    """Lista a biblioteca de prompts prontos e devolve {titulo, texto, id, read_only}."""
    from . import prompts
    groups = prompts.grouped()
    print(ui.CYAN + "\nPrompts prontos" + ui.RESET)
    index: list[dict[str, Any]] = []
    for key, label in prompts.CATEGORIES.items():
        items = groups.get(key) or []
        if not items:
            continue
        print(ui.BOLD + f" {label}" + ui.RESET)
        for item in items:
            index.append(item)
            mark = ui.DIM + " (só leitura)" + ui.RESET if prompts.is_read_only(item["id"]) else ""
            print(f"  [{len(index)}] {item['titulo']}{mark}")
            print(ui.DIM + f"       {item['descricao']}" + ui.RESET)
    raw = ui.safe_input("Número do prompt (ENTER para cancelar): ").strip()
    if not raw.isdigit() or not 1 <= int(raw) <= len(index):
        if raw:
            print(ui.YELLOW + "Seleção inválida." + ui.RESET)
        return None
    item = index[int(raw) - 1]
    if item.get("aviso"):
        print(ui.YELLOW + item["aviso"] + ui.RESET)
        if ui.safe_input("Confirmar que este APK é seu ou você tem autorização? (s/N): ").strip().lower() != "s":
            return None
    text = item["prompt"]
    if prompts.needs_input(item["id"]):
        extra = ui.safe_input("Informe o dado pedido (ou ENTER para deixar a IA decidir): ").strip()
        if extra:
            text = text.rstrip() + "\n\nDADOS FORNECIDOS:\n" + extra
    return {"titulo": item["titulo"], "texto": text, "id": item["id"],
            "read_only": prompts.is_read_only(item["id"])}


def _edit_and_rebuild(ui, decoded: Path, instruction: str | None = None,
                      read_only: bool = False, dry_run: bool = False) -> None:
    from datetime import datetime

    from . import builder
    if not (decoded / "apktool.yml").is_file():
        print(ui.YELLOW + "Essa pasta não é uma saída do Apktool (opção 5 do menu principal)." + ui.RESET)
        return
    print(ui.YELLOW + "Use só em APK seu ou que você tem autorização para modificar." + ui.RESET)
    if instruction is None:
        print(ui.DIM + " Digite a tarefa ou [P] para escolher um prompt pronto." + ui.RESET)
        instruction = ui.safe_input("O que a IA deve fazer? (P = prompts, ENTER = só reconstruir): ").strip()
        if instruction.lower() == "p":
            chosen = _choose_ready_prompt(ui)
            if chosen is None:
                print(ui.YELLOW + "Nenhum prompt escolhido." + ui.RESET)
                return
            print(ui.GREEN + f"Prompt: {chosen['titulo']}" + ui.RESET)
            instruction = chosen["texto"]
            read_only = read_only or chosen["read_only"]
    if read_only:
        _diagnose_with_ai(ui, decoded, instruction)
        return
    print(f"A IA vai editar arquivos em {decoded}.")
    print(ui.DIM + "O backup é feito na opção [B] Backup, separadamente." + ui.RESET)
    if dry_run:
        print(ui.DIM + "Modo revisão: nada é gravado até você aprovar o diff." + ui.RESET)
    if ui.safe_input("Continuar? (s/N): ").strip().lower() != "s":
        return
    if dry_run:
        _review_then_apply(ui, decoded, instruction)
        return

    def build_fn():
        name = decoded.name.replace("_apktool", "") or "app"
        work = ui.BUILDS / f"{name}_{datetime.now():%Y%m%d_%H%M%S}"
        result = builder.build_pipeline(decoded, work, ui.KEYSTORE, builder.DEFAULT_ALIAS,
                                        builder.DEFAULT_STOREPASS, [], lambda m: print(ui.CYAN + " · " + m + ui.RESET))
        _print_build(ui, result)
        return result

    out = fix_loop(decoded, instruction, build_fn, lambda prompt: ask_with_fallback(ui, decoded, prompt),
                   lambda q: ui.safe_input(q + " (s/N): ").strip().lower() == "s", print)
    if out["ok"]:
        print(ui.GREEN + f"\nAPK pronto: {out['result'].get('final_apk')}" + ui.RESET)
    else:
        print(ui.RED + "\n" + out["message"] + ui.RESET)
        print(ui.DIM + "Para desfazer, use [B] Backup e restaure um backup anterior." + ui.RESET)


def _diagnose_with_ai(ui, decoded: Path, instruction: str) -> None:
    """Tarefa de diagnóstico: a IA só lê e explica; nenhum arquivo é alterado."""
    provider = load_provider()
    print(ui.CYAN + "\nDiagnóstico (somente leitura)" + ui.RESET)
    if provider != PROVIDER_GATEWAY:
        print(ui.YELLOW + f"O provedor {provider} não permite bloquear gravações pelo ReaDroid." + ui.RESET)
        print(ui.DIM + "Para garantir que nada seja alterado, use o gateway (agente interno)." + ui.RESET)
        if ui.safe_input("Continuar mesmo assim? (s/N): ").strip().lower() != "s":
            return
    print(ui.DIM + "A IA vai ler os arquivos e responder; nada será gravado." + ui.RESET)
    if ui.safe_input("Continuar? (s/N): ").strip().lower() != "s":
        return
    if provider == PROVIDER_GATEWAY:
        res = run_gateway_agent(decoded, instruction, emit=print, read_only=True)
    else:
        res = ask_with_fallback(ui, decoded, instruction)
    if res.get("ok"):
        print(ui.GREEN + "\n" + str(res.get("message") or "Concluído.") + ui.RESET)
    else:
        print(ui.RED + "\n" + str(res.get("message") or "A IA não respondeu.") + ui.RESET)
        _offer_resume(ui, decoded, res)


def _offer_resume(ui, decoded: Path, res: dict[str, Any]) -> None:
    """Se o agente bateu no limite de passos, oferece retomar a conversa salva."""
    from . import agent as _agent_mod
    session_id = res.get("session_id")
    if not session_id:
        return
    print(ui.CYAN + "\nA conversa da IA foi salva nesta pasta (" + _agent_mod.SESSIONS_DIRNAME + ")." + ui.RESET)
    if ui.safe_input("Retomar de onde parou agora? (s/N): ").strip().lower() != "s":
        print(ui.DIM + "Você pode retomar depois pela opção 09 Retomar tarefa no menu de IA." + ui.RESET)
        return
    follow = ui.safe_input("Mensagem extra para a IA (ENTER para só retomar): ").strip()
    res2 = run_gateway_agent(decoded, follow or "continue", emit=print, session_id=session_id)
    if res2.get("ok"):
        print(ui.GREEN + "\n" + str(res2.get("message") or "Concluído.") + ui.RESET)
    else:
        print(ui.RED + "\n" + str(res2.get("message") or "A IA não respondeu.") + ui.RESET)
        if res2.get("session_id"):
            print(ui.DIM + "A sessão continua salva; tente de novo mais tarde." + ui.RESET)


def _review_then_apply(ui, decoded: Path, instruction: str) -> None:
    """Roda o agente em modo proposta, mostra o diff e só grava se você aprovar."""
    from datetime import datetime

    from . import agent, builder
    provider = load_provider()
    if provider != PROVIDER_GATEWAY:
        print(ui.YELLOW + f"O provedor {provider} edita os arquivos direto; não há diff para revisar." + ui.RESET)
        print(ui.DIM + "Use o gateway para revisar antes de aplicar." + ui.RESET)
        return
    res = run_gateway_agent(decoded, instruction, emit=print, dry_run=True)
    res = _maybe_resume_dry_run(ui, decoded, res)
    proposals = res.get("proposals") or {}
    if not proposals:
        print(ui.YELLOW + "\nA IA não propôs nenhuma alteração." + ui.RESET)
        if res.get("message"):
            print(ui.DIM + str(res["message"]) + ui.RESET)
        return
    print(ui.CYAN + f"\nPropostas ({len(proposals)} arquivo(s)):" + ui.RESET)
    for line in agent.summarize_proposals(decoded, proposals):
        print(" " + ui.sanitize(line))
    if ui.safe_input("\nVer o diff completo? (s/N): ").strip().lower() == "s":
        for rel in sorted(proposals):
            print(ui.BOLD + f"\n--- {rel} ---" + ui.RESET)
            for line in agent.diff_proposal(decoded, rel, proposals[rel]):
                color = ui.GREEN if line.startswith("+") and not line.startswith("+++") else (
                    ui.RED if line.startswith("-") and not line.startswith("---") else ui.DIM)
                print(color + ui.sanitize(line) + ui.RESET)
    if ui.safe_input("\nAplicar estas alterações? (s/N): ").strip().lower() != "s":
        print(ui.DIM + "Nada foi gravado." + ui.RESET)
        return
    applied = agent.apply_proposals(decoded, proposals)
    if not applied["ok"]:
        print(ui.RED + "Algumas gravações falharam: " + "; ".join(applied["problems"]) + ui.RESET)
    print(ui.GREEN + f"Gravado: {', '.join(applied['written']) or 'nada'}" + ui.RESET)
    if ui.safe_input("Reconstruir o APK agora? (s/N): ").strip().lower() != "s":
        return
    name = decoded.name.replace("_apktool", "") or "app"
    work = ui.BUILDS / f"{name}_{datetime.now():%Y%m%d_%H%M%S}"
    result = builder.build_pipeline(decoded, work, ui.KEYSTORE, builder.DEFAULT_ALIAS,
                                    builder.DEFAULT_STOREPASS, [],
                                    lambda m: print(ui.CYAN + " · " + m + ui.RESET))
    _print_build(ui, result)
    if result.get("ok"):
        print(ui.GREEN + f"\nAPK pronto: {result.get('final_apk')}" + ui.RESET)
    else:
        print(ui.RED + "\nA reconstrução não terminou." + ui.RESET)


def _maybe_resume_dry_run(ui, decoded: Path, res: dict[str, Any]) -> dict[str, Any]:
    """No modo revisão, um limite de passos sem propostas ainda pode ser retomado: pergunta e
    roda a continuação na MESMA sessão, também em dry_run, devolvendo o resultado final."""
    if not res.get("limit_reached"):
        return res
    proposals = res.get("proposals") or {}
    session_id = res.get("session_id")
    if session_id and ui.safe_input(
            "\nA IA atingiu o limite de passos. Retomar de onde parou? (s/N): ").strip().lower() == "s":
        res2 = run_gateway_agent(decoded, "continue", emit=print, dry_run=True, session_id=session_id)
        res2 = _maybe_resume_dry_run(ui, decoded, res2)  # pode precisar de mais de uma retomada
        if res2.get("proposals") or not res2.get("limit_reached"):
            return res2
    if not proposals:
        print(ui.YELLOW + "\nA IA não propôs nenhuma alteração." + ui.RESET)
        if res.get("message"):
            print(ui.DIM + str(res["message"]) + ui.RESET)
    return res


def _recreate_with_ai(ui, decoded: Path) -> None:
    """Recria/reescreve uma parte do app do zero (ou o app inteiro, módulo por módulo).
    Reaproveita o mesmo ciclo editar -> reconstruir -> corrigir do _edit_and_rebuild, só que
    com um prompt de recriação em vez de edição pontual. Pensado para o provedor codex
    (modo automático, várias etapas sozinho), mas funciona com qualquer provedor ativo."""
    from datetime import datetime

    from . import builder
    if not (decoded / "apktool.yml").is_file():
        print(ui.YELLOW + "Essa pasta não é uma saída do Apktool (opção 5 do menu principal)." + ui.RESET)
        return
    provider = load_provider()
    print(ui.YELLOW + "Recriação de código é uma mudança grande. Use só em APK seu ou autorizado." + ui.RESET)
    print(ui.DIM + f"Provedor ativo: {PROVIDER_LABELS[provider]}" + ui.RESET)
    target = ui.safe_input(
        "O que recriar? (ex.: 'a tela de login', 'o parser de XML', "
        "'tudo, modernizando o código') : "
    ).strip()
    if not target:
        print(ui.YELLOW + "Nada informado." + ui.RESET)
        return
    print(f"A IA vai reescrever arquivos em {decoded}.")
    print(ui.DIM + "O backup é feito na opção [B] Backup, separadamente." + ui.RESET)
    if ui.safe_input("Continuar? (s/N): ").strip().lower() != "s":
        return

    def build_fn():
        name = decoded.name.replace("_apktool", "") or "app"
        work = ui.BUILDS / f"{name}_{datetime.now():%Y%m%d_%H%M%S}"
        result = builder.build_pipeline(decoded, work, ui.KEYSTORE, builder.DEFAULT_ALIAS,
                                        builder.DEFAULT_STOREPASS, [], lambda m: print(ui.CYAN + " · " + m + ui.RESET))
        _print_build(ui, result)
        return result

    instruction = PROMPT_RECREATE + target
    out = fix_loop(decoded, instruction, build_fn, lambda prompt: ask_with_fallback(ui, decoded, prompt),
                   lambda q: ui.safe_input(q + " (s/N): ").strip().lower() == "s", print,
                   rules=RECREATE_RULES)
    if out["ok"]:
        print(ui.GREEN + f"\nAPK recriado e reconstruído: {out['result'].get('final_apk')}" + ui.RESET)
    else:
        print(ui.RED + "\n" + out["message"] + ui.RESET)
        print(ui.DIM + "Para desfazer, use [B] Backup e restaure um backup anterior." + ui.RESET)


def _choose_provider(ui) -> None:
    current = load_provider()
    print(ui.CYAN + "\nProvedores disponíveis:" + ui.RESET)
    for i, prov in enumerate(PROVIDERS, 1):
        mark = " (atual)" if prov == current else ""
        print(f" [{i}] {PROVIDER_LABELS[prov]}{mark}")
    raw = ui.safe_input("Escolha o provedor (ENTER para cancelar): ").strip()
    if not raw:
        return
    try:
        chosen = PROVIDERS[int(raw) - 1]
    except (ValueError, IndexError):
        print(ui.YELLOW + "Opção inválida." + ui.RESET)
        return
    save_provider(chosen)
    print(ui.GREEN + f"Provedor ativo: {PROVIDER_LABELS[chosen]}" + ui.RESET)
    if chosen == PROVIDER_CODEX and not find_codex():
        print(ui.YELLOW + "Aviso: não achei o binário `codex` no PATH agora. Confirme que ele "
              "funciona direto no Termux (fora do ReaDroid) antes de usar." + ui.RESET)
    if chosen == PROVIDER_OPENCODE and load_key() is None:
        print(ui.YELLOW + "Aviso: o provedor opencode precisa de uma chave do OpenRouter (opção [10])." + ui.RESET)
    if chosen == PROVIDER_GATEWAY and not load_gateway_key():
        print(ui.YELLOW + "Configure URL, chave e modelo do gateway na opção [10]." + ui.RESET)


def run_menu(ui) -> None:
    """Menu 13. `ui` é o módulo app (cores, safe_input, sanitize, OUTPUTS, REPORTS, BUILDS, KEYSTORE)."""
    print(ui.CYAN + "\nASSISTENTE DE IA (opcional)" + ui.RESET)
    print(ui.DIM + "O ReaDroid funciona normalmente sem isto. Ignore se não quiser usar IA." + ui.RESET)
    provider = load_provider()
    configured = load_gateway_key() if provider == PROVIDER_GATEWAY else load_key() if provider == PROVIDER_OPENCODE else True
    if not configured and provider in (PROVIDER_OPENCODE, PROVIDER_GATEWAY):
        print("Nenhuma chave configurada para o provedor ativo.")
        if ui.safe_input("Configurar agora? (s/N): ").strip().lower() == "s":
            _setup(ui, provider)
    _menu_loop(ui)


def _menu_loop(ui) -> None:
    consented = False
    while True:
        provider = load_provider()
        status = (f"gateway/{load_model()}" if provider == PROVIDER_GATEWAY else
                  f"openrouter/{load_model()}" if provider == PROVIDER_OPENCODE else "binário global do Termux")
        print()
        print(_ui.BOLD + _ui.YELLOW + "▸ INTELIGÊNCIA ARTIFICIAL" + _ui.RESET)
        print(_ui.GRAY + f" Provedor: {PROVIDER_LABELS[provider]} · {status}" + _ui.RESET)
        print(_ui.GRAY + "─" * 44 + _ui.RESET)
        print(" " + _ui.CYAN + "01" + _ui.RESET + " — Abrir o assistente numa pasta de APK")
        print(" " + _ui.CYAN + "02" + _ui.RESET + " — Resumir o app")
        print(" " + _ui.CYAN + "03" + _ui.RESET + " — Cruzar relatórios do ReaDroid com o código")
        print(" " + _ui.CYAN + "04" + _ui.RESET + " — Editar com a IA e reconstruir")
        print(" " + _ui.CYAN + "05" + _ui.RESET + " — Recriar um trecho do app do zero")
        print(" " + _ui.CYAN + "06" + _ui.RESET + " — Explicar um erro de reconstrução")
        print(" " + _ui.CYAN + "07" + _ui.RESET + " — Pergunta livre sobre o APK")
        print(" " + _ui.CYAN + "08" + _ui.RESET + " — Testar / diagnosticar")
        print(" " + _ui.CYAN + "09" + _ui.RESET + " — Retomar tarefa (continua de onde a IA parou)")
        print(" " + _ui.CYAN + "10" + _ui.RESET + " — Configurar provedor/chave")
        print(_ui.BOLD + _ui.YELLOW + "▸ ATALHOS" + _ui.RESET)
        print(" " + _ui.CYAN + "R " + _ui.RESET + "— Prompts prontos (VIP, tradução, diagnóstico…)")
        print(" " + _ui.CYAN + "D " + _ui.RESET + "— Editar com revisão do diff antes de aplicar")
        print(" " + _ui.CYAN + "B " + _ui.RESET + "— Backup da pasta decodificada")
        print(_ui.BOLD + _ui.YELLOW + "▸ CONFIGURAÇÃO" + _ui.RESET)
        print(" " + _ui.CYAN + "11" + _ui.RESET + " — Trocar modelo")
        print(" " + _ui.CYAN + "12" + _ui.RESET + " — Limite de passos do agente (atual: %d)" % load_agent_max_steps())
        print(" " + _ui.CYAN + "P " + _ui.RESET + "— Trocar provedor de IA")
        print(" " + _ui.CYAN + "13" + _ui.RESET + " — Desativar IA (apaga chave e config)")
        print(" " + _ui.CYAN + "0 " + _ui.RESET + "— Voltar")
        choice = ui.safe_input("IA > ").strip()
        if choice in ("", "0"):
            return
        low = choice.lower()
        if low == "p":
            _choose_provider(ui)
            continue
        if low == "l":  # atalho antigo mantido para quem já usava
            _change_agent_limit(ui)
            continue
        if low == "r":
            folder = _choose_dir(ui)
            if folder is None:
                print(ui.YELLOW + "Pasta não encontrada." + ui.RESET)
                continue
            chosen = _choose_ready_prompt(ui)
            if chosen is None:
                continue
            _edit_and_rebuild(ui, folder, instruction=chosen["texto"],
                              read_only=chosen["read_only"])
            continue
        if low == "d":
            folder = _choose_dir(ui)
            if folder is None:
                print(ui.YELLOW + "Pasta não encontrada." + ui.RESET)
                continue
            _edit_and_rebuild(ui, folder, dry_run=True)
            continue
        if low == "b":
            folder = _choose_dir(ui)
            if folder is None:
                print(ui.YELLOW + "Pasta não encontrada." + ui.RESET)
                continue
            _backup_menu(ui, folder)
            continue
        if choice in ("1", "2", "3", "4", "5", "6", "7"):
            if not consented:
                print(ui.YELLOW + PRIVACY + ui.RESET)
                if ui.safe_input("Continuar? (s/N): ").strip().lower() != "s":
                    continue
                consented = True
            folder = _choose_dir(ui)
            if folder is None:
                print(ui.YELLOW + "Pasta não encontrada." + ui.RESET)
                continue
            res: dict[str, Any] | None = None
            if choice == "1":
                res = open_interactive(folder)
            elif choice == "2":
                res = ask_with_fallback(ui, folder, PROMPT_SUMMARY)
            elif choice == "3":
                ctx = build_report_context(ui.REPORTS, folder)
                if not ctx:
                    print(ui.YELLOW + "Sem relatórios para este APK. Rode antes as opções 1, 2 e 3 do menu principal." + ui.RESET)
                    continue
                res = ask_with_fallback(ui, folder, PROMPT_CROSS + ctx)
            elif choice == "4":
                _edit_and_rebuild(ui, folder)
            elif choice == "5":
                _recreate_with_ai(ui, folder)
            elif choice == "6":
                err = ui.safe_input("Cole o erro (uma linha) ou ENTER para cancelar: ").strip()
                if not err:
                    continue
                res = ask_with_fallback(ui, folder, PROMPT_BUILD + err[:4000])
            else:
                question = ui.safe_input("Sua pergunta: ").strip()
                if not question:
                    continue
                res = ask_with_fallback(ui, folder, question[:4000])
            if res is not None:
                print((ui.GREEN if res["ok"] else ui.YELLOW) + res["message"] + ui.RESET)
                _offer_resume(ui, folder, res or {})
        elif choice == "8":
            _run_checks(ui)
        elif choice == "9":
            _resume_menu(ui)
        elif choice == "10":
            _setup(ui)
        elif choice == "11":
            _change_model(ui)
        elif choice == "12":
            _change_agent_limit(ui)
        elif choice == "13":
            if ui.safe_input("Apagar chave e configuração da IA (opencode e codex)? (s/N): ").strip().lower() == "s":
                gone = disable()
                print(ui.GREEN + ("Removido: " + ", ".join(gone) if gone else "Nada para remover.") + ui.RESET)
                return
        else:
            print(ui.YELLOW + "Opção inválida." + ui.RESET)


def _resume_menu(ui) -> None:
    """Retoma uma sessão do agente salva quando o limite de passos foi atingido."""
    folder = _choose_dir(ui)
    if folder is None:
        print(ui.YELLOW + "Pasta não encontrada." + ui.RESET)
        return
    from . import agent
    sessions = agent.list_sessions(folder)
    if not sessions:
        print(ui.DIM + "Nenhuma sessão salva nesta pasta. Ela aparece quando a IA atinge "
              "o limite de passos sem terminar a tarefa." + ui.RESET)
        return
    print(ui.CYAN + f"\nSessões salvas em {folder.name}:" + ui.RESET)
    for i, sess in enumerate(sessions, 1):
        print(f" [{i}] {sess['id']}")
    raw = ui.safe_input("Qual sessão retomar? (ENTER = cancelar): ").strip()
    if not raw:
        return
    try:
        chosen = sessions[int(raw) - 1]
    except (ValueError, IndexError):
        print(ui.YELLOW + "Opção inválida." + ui.RESET)
        return
    follow = ui.safe_input("Mensagem extra para a IA (ENTER para só retomar): ").strip()
    res = run_gateway_agent(folder, follow or "continue", emit=print, session_id=chosen["id"])
    if res.get("ok"):
        print(ui.GREEN + "\n" + str(res.get("message") or "Concluído.") + ui.RESET)
    else:
        print(ui.RED + "\n" + str(res.get("message") or "A IA não respondeu.") + ui.RESET)
        _offer_resume(ui, folder, res)
