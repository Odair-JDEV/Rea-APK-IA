"""Atualização do ReaDroid pela cópia Git do projeto.

A opção do menu pergunta ao GitHub se há commits novos, mostra o que viria e,
com a sua confirmação, avança a branch local (fast-forward). Limites de
segurança, todos verificáveis:

- só funciona se o projeto for um repositório Git com `origin` configurado;
- recusa atualizar se houver arquivos seus alterados (git status não vazio);
- recusa se a branch local divergiu de `origin` (ex.: você fez commits próprios);
- nunca faz merge automático, nunca força push, nunca apaga nada;
- `git pull --ff-only` já é seguro por si, e aqui só roda depois de você aceitar.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

TIMEOUT = 60


def _git(repo: Path, *args: str) -> tuple[int, str]:
    try:
        result = subprocess.run(["git", *args], cwd=repo, capture_output=True,
                                text=True, timeout=TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode, output.strip()


def check_update(repo: Path) -> dict[str, Any]:
    """Consulta o remoto sem alterar nada. `ok` diz se a checagem funcionou."""
    if not (repo / ".git").exists():
        return {"ok": False, "message": "Esta cópia não é um repositório Git; baixe o projeto novamente."}
    code, _ = _git(repo, "rev-parse", "--is-inside-work-tree")
    if code != 0:
        return {"ok": False, "message": "Não foi possível consultar o Git nesta pasta."}
    code, remote = _git(repo, "remote", "get-url", "origin")
    if code != 0 or not remote:
        return {"ok": False, "message": "Nenhum remote 'origin' configurado."}
    code, branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    if code != 0 or not branch or branch == "HEAD":
        return {"ok": False, "message": "Não foi possível identificar a branch atual (checkout destacado?)."}
    code, out = _git(repo, "fetch", "origin", branch)
    if code != 0:
        return {"ok": False, "message": f"Falha ao contatar o servidor:\n{out[-300:]}"}
    code, status = _git(repo, "status", "--porcelain")
    if code != 0:
        return {"ok": False, "message": "Não foi possível ler o estado dos arquivos."}
    dirty = [line for line in status.splitlines() if line.strip()]
    if dirty:
        preview = "\n".join(dirty[:10])
        extra = f"\n  ... (+{len(dirty) - 10})" if len(dirty) > 10 else ""
        return {"ok": False, "dirty": True, "changed": len(dirty),
                "message": ("Há arquivos alterados por você; atualizar por cima pode perder essas mudanças.\n"
                            f"{preview}{extra}\n"
                            "Guarde ou reverta as mudanças antes de atualizar.")}
    code, behind = _git(repo, "rev-list", "--count", f"HEAD..origin/{branch}")
    if code != 0:
        return {"ok": False, "message": "Não foi possível comparar com o remoto."}
    code, ahead = _git(repo, "rev-list", "--count", f"origin/{branch}..HEAD")
    if code != 0:
        return {"ok": False, "message": "Não foi possível comparar com o remoto."}
    if ahead != "0":
        return {"ok": False, "diverged": True,
                "message": (f"Sua branch ({branch}) tem {ahead} commit(s) que não estão no remoto; "
                            "o ReaDroid não sobrescreve commits seus. Envie-os ou volte atrás manualmente.")}
    if behind == "0":
        return {"ok": True, "updated": False, "branch": branch,
                "message": "Você já está na versão mais recente."}
    code, log = _git(repo, "log", "--oneline", f"HEAD..origin/{branch}")
    if code != 0:
        log = ""
    return {"ok": True, "updated": True, "branch": branch, "behind": int(behind),
            "commits": [line for line in log.splitlines() if line.strip()][:20],
            "message": f"{behind} atualização(ões) disponível(is)."}


def apply_update(repo: Path, branch: str) -> dict[str, Any]:
    """Avança a branch local para o remoto (fast-forward apenas)."""
    code, out = _git(repo, "merge", "--ff-only", f"origin/{branch}")
    if code != 0:
        return {"ok": False, "message": f"A atualização não pôde ser aplicada:\n{out[-400:]}"}
    code, head = _git(repo, "log", "--oneline", "-1")
    return {"ok": True, "message": f"Atualizado. {head or ''}".strip()}
