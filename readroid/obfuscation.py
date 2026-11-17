"""Pista de ofuscação: nomes de arquivos curtos e classes DEX com nomes sem sentido.

É só uma pista, não um veredito: apps legítimos também minificam, e a lista de arquivos
não prova nada sobre o código. Por isso a função devolve "unknown" quando não há indício
nem contrário, e nunca bloqueia nada.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Any

SHORT_NAME_RE = re.compile(r"^[a-z]{1,2}\.(?:smali|xml|json|png)$", re.IGNORECASE)
DEX_CLASS_HINT_RE = re.compile(rb"(?:^|\x00)L[a-z]{1,2}/[a-z]{1,2};")


def likely_obfuscated(apk: Path, min_short: int = 40) -> dict[str, Any]:
    """Conta nomes curtíssimos entre os arquivos do ZIP. Nunca lê o conteúdo inteiro."""
    short = 0
    total = 0
    try:
        with zipfile.ZipFile(apk) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                total += 1
                if SHORT_NAME_RE.match(info.filename.rsplit("/", 1)[-1]):
                    short += 1
    except (OSError, zipfile.BadZipFile) as exc:
        return {"obfuscated": None, "short_names": 0, "total": 0,
                "message": f"Não foi possível avaliar a ofuscação: {exc}"}

    if total == 0:
        return {"obfuscated": None, "short_names": 0, "total": 0,
                "message": "APK sem arquivos lidos; não é possível avaliar a ofuscação."}
    ratio = short / total
    if short >= min_short and ratio >= 0.15:
        return {"obfuscated": True, "short_names": short, "total": total, "ratio": round(ratio, 3),
                "message": f"Muitos nomes curtíssimos ({short} de {total} arquivos): o código parece ofuscado. "
                           "Isso é normal em apps de loja e não indica problema por si só."}
    return {"obfuscated": False, "short_names": short, "total": total, "ratio": round(ratio, 3),
            "message": f"Sem indício forte de ofuscação ({short} nomes curtos de {total} arquivos)."}


def detect(apk: Path) -> dict[str, Any]:
    """Alias curto usado pelo menu."""
    return likely_obfuscated(apk)
