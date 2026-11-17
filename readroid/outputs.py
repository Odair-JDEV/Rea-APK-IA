"""Destino dos APKs reconstruídos, escolhido pelo usuário.

Por padrão o ReaDroid copia o APK pronto para `~/storage/downloads/ReaDroid` (Termux).
Esta configuração deixa o usuário escolher outra pasta do celular — por exemplo
`/storage/emulated/0/Download/Meus APKs` — e vale para o menu 11 e para o assistente
guiado. A pasta fica em `~/.readroid/settings.json`, fora do projeto, junto das
outras preferências.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

SETTINGS_FILE = Path(os.environ.get("READROID_HOME") or (Path.home() / ".readroid")) / "settings.json"

DEFAULT_SUBDIR = "ReaDroid"


def load_output_dir() -> str:
    """Caminho da pasta de saída configurada; vazio quando é o padrão."""
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    value = data.get("apk_output_dir") if isinstance(data, dict) else None
    return str(value).strip() if isinstance(value, str) else ""


def save_output_dir(path: str | None) -> None:
    """Grava a pasta escolhida; None ou vazio volta ao padrão."""
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    clean = str(path or "").strip()
    if clean:
        data["apk_output_dir"] = clean
    else:
        data.pop("apk_output_dir", None)
    SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_output_dir(path: str | None = None) -> Path:
    """Pasta onde a cópia amigável do APK deve ficar, já criada quando possível.

    A ordem é: argumento explícito, configuração salva, padrão do Termux
    (`~/storage/downloads/ReaDroid`). Se o padrão não existir (fora do Termux,
    storage não liberado), cai para `builds/` do projeto, que sempre existe.
    """
    raw = (path or load_output_dir() or "").strip()
    if raw:
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute():
            candidate = Path.home() / "storage" / "shared" / candidate
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
        except OSError:
            return Path.cwd() / "builds"
    downloads = Path.home() / "storage" / "downloads"
    if downloads.is_dir():
        candidate = downloads / DEFAULT_SUBDIR
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
        except OSError:
            pass
    return Path.cwd() / "builds"


def copy_to_output(apk: Path, output_dir: Path) -> Path | None:
    """Copia o APK para a pasta de saída e devolve o destino; None quando falhar."""
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        dest = output_dir / apk.name
        # Nome repetido não é sobrescrito: cada build tem carimbo de tempo, mas o
        # usuário pode rodar o mesmo build duas vezes na mesma pasta.
        if dest.exists():
            stem, suffix = apk.stem, apk.suffix
            index = 2
            while dest.exists():
                dest = output_dir / f"{stem}_{index}{suffix}"
                index += 1
        shutil.copy2(apk, dest)
        return dest
    except OSError:
        return None
