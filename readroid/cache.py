"""Cache de análise por SHA-256 do APK.

Analisar o mesmo APK duas vezes é desperdício: a inspeção e a varredura de strings
são determinísticas para o mesmo conteúdo. O cache fica em `reports/.cache/` e guarda
apenas o resultado já sanitizado que iria para o relatório.

Como o SHA-256 identifica o conteúdo, um APK alterado (mesmo nome, outro conteúdo)
tem hash diferente e não reaproveita a entrada antiga.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

CACHE_DIR_NAME = ".cache"
MAX_CACHE_FILES = 200


def cache_dir(reports_dir: Path) -> Path:
    return reports_dir / CACHE_DIR_NAME


def _path_for(reports_dir: Path, kind: str, sha256: str) -> Path:
    safe = "".join(ch for ch in sha256 if ch.isalnum() or ch in "-_")[:64]
    return cache_dir(reports_dir) / f"{kind}_{safe}.json"


def load(reports_dir: Path, kind: str, sha256: str) -> dict[str, Any] | None:
    try:
        data = json.loads(_path_for(reports_dir, kind, sha256).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def store(reports_dir: Path, kind: str, sha256: str, data: dict[str, Any]) -> None:
    target = _path_for(reports_dir, kind, sha256)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(".tmp")
        temp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        os.replace(temp, target)
    except OSError:
        return
    _prune(target.parent)


def _prune(folder: Path) -> None:
    """Mantém o cache limitado: apaga os arquivos mais antigos quando passa do limite."""
    try:
        files = sorted(folder.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        return
    for old in files[MAX_CACHE_FILES:]:
        try:
            old.unlink()
        except OSError:
            continue


def cached(reports_dir: Path, kind: str, sha256: str,
           compute: Callable[[], dict[str, Any]]) -> tuple[dict[str, Any], bool]:
    """Devolve (resultado, veio_do_cache)."""
    found = load(reports_dir, kind, sha256)
    if found is not None:
        return found, True
    data = compute()
    if isinstance(data, dict):
        store(reports_dir, kind, sha256, data)
    return data, False
