"""Comparação entre o APK original e o reconstruído, e relatório legível.

A comparação responde à pergunta mais útil depois de editar: "o que mudou de fato?".
Ela olha o conteúdo do ZIP (nomes, tamanhos, hashes) e o manifesto, sem executar nada.
"""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path
from typing import Any

MAX_ENTRIES = 20000


def _entries(path: Path) -> dict[str, tuple[int, str]]:
    """nome -> (tamanho, sha256 do conteúdo). Arquivos ilegíveis ficam com hash vazio."""
    result: dict[str, tuple[int, str]] = {}
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            if len(result) >= MAX_ENTRIES:
                break
            digest = ""
            try:
                if info.file_size <= 8 * 1024 * 1024:
                    digest = hashlib.sha256(archive.read(info)).hexdigest()
            except (OSError, RuntimeError, zipfile.BadZipFile):
                digest = ""
            result[info.filename] = (info.file_size, digest)
    return result


def compare_apks(original: Path, rebuilt: Path) -> dict[str, Any]:
    """Diferença entre dois APKs: arquivos adicionados, removidos, alterados e tamanho."""
    before = _entries(original)
    after = _entries(rebuilt)
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = sorted(name for name in set(before) & set(after)
                     if before[name][1] and after[name][1] and before[name] != after[name])
    size_before = original.stat().st_size
    size_after = rebuilt.stat().st_size
    return {
        "original": original.name,
        "rebuilt": rebuilt.name,
        "size_before": size_before,
        "size_after": size_after,
        "size_delta": size_after - size_before,
        "entries_before": len(before),
        "entries_after": len(after),
        "added": added[:500],
        "removed": removed[:500],
        "changed": changed[:500],
        "added_count": len(added),
        "removed_count": len(removed),
        "changed_count": len(changed),
        "manifest_changed": "AndroidManifest.xml" in changed,
        "note": "Comparação por conteúdo do ZIP; não prova comportamento em execução.",
    }


def format_comparison(result: dict[str, Any], limit: int = 12) -> list[str]:
    """Linhas prontas para o terminal."""
    delta = result["size_delta"]
    sign = "+" if delta >= 0 else "-"
    lines = [
        f"Tamanho: {result['size_before'] // 1024} KB → {result['size_after'] // 1024} KB "
        f"({sign}{abs(delta) // 1024} KB)",
        f"Arquivos: {result['entries_before']} → {result['entries_after']} "
        f"(+{result['added_count']} / -{result['removed_count']} / ~{result['changed_count']})",
    ]
    if result["manifest_changed"]:
        lines.append("O AndroidManifest.xml foi alterado.")
    for label, key in (("Adicionados", "added"), ("Removidos", "removed"), ("Alterados", "changed")):
        items = result.get(key) or []
        if not items:
            continue
        lines.append(f"{label}:")
        lines.extend("  " + name for name in items[:limit])
        if len(items) > limit:
            lines.append(f"  ... (+{len(items) - limit})")
    return lines
