"""Checagens antes/depois do build: espaço em disco, minSdk, versão do dispositivo.

Tudo é leitura e degrada com elegância: se não for possível medir, a checagem
devolve `ok=None` com uma mensagem, nunca um falso "está tudo certo".
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

MIN_FREE_BYTES = 200 * 1024 * 1024


def free_bytes(path: Path) -> int | None:
    try:
        return shutil.disk_usage(path).free
    except OSError:
        return None


def check_disk_space(path: Path, required: int = MIN_FREE_BYTES) -> dict[str, Any]:
    """Antes de reconstruir: avisa se o espaço livre pode não bastar."""
    free = free_bytes(path)
    if free is None:
        return {"ok": None, "message": "Não foi possível medir o espaço em disco."}
    needed_text = f"{required // (1024 * 1024)} MB"
    free_text = f"{free // (1024 * 1024)} MB"
    if free < required:
        return {"ok": False, "message": f"Pouco espaço livre: {free_text} (recomendado: {needed_text}).", "free": free}
    return {"ok": True, "message": f"Espaço livre: {free_text}.", "free": free}


def decoded_size(path: Path) -> int:
    total = 0
    for item in path.rglob("*"):
        try:
            if item.is_file():
                total += item.stat().st_size
        except OSError:
            continue
    return total


def estimate_build_space(decoded: Path) -> int:
    """Estimativa conservadora: o dobro da pasta decodificada, com piso de 200 MB."""
    return max(MIN_FREE_BYTES, decoded_size(decoded) * 2)


# ------------------------------------------------------------------ minSdk / dispositivo

# Aceita "minSdkVersion: 21" e também a forma aninhada dentro de sdkInfo.
_SDK_RE = re.compile(r"minSdkVersion\s*:\s*['\"]?(\d{1,3})", re.IGNORECASE)


def manifest_min_sdk(decoded: Path) -> int | None:
    """Lê minSdk do apktool.yml ou do AndroidManifest.xml (texto)."""
    for name, pattern in (("apktool.yml", _SDK_RE),
                          ("AndroidManifest.xml", re.compile(r'android:minSdkVersion="(\d{1,3})"'))):
        path = decoded / name
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        match = pattern.search(text)
        if match:
            try:
                return int(match.group(1))
            except (TypeError, ValueError):
                continue
    return None


def device_sdk() -> int | None:
    """Versão do Android do dispositivo conectado via adb, se houver exatamente um."""
    adb = shutil.which("adb")
    if not adb:
        return None
    try:
        result = subprocess.run([adb, "shell", "getprop", "ro.build.version.sdk"],
                                capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    match = re.search(r"\d{1,3}", result.stdout or "")
    return int(match.group(0)) if match else None


def check_min_sdk(decoded: Path, sdk: int | None = None) -> dict[str, Any]:
    """Compara o minSdk do APK com a versão do dispositivo, quando ambos são conhecidos."""
    required = manifest_min_sdk(decoded)
    if required is None:
        return {"ok": None, "message": "minSdkVersion não encontrado no apktool.yml/manifesto."}
    device = sdk if sdk is not None else device_sdk()
    if device is None:
        return {"ok": None, "min_sdk": required,
                "message": f"minSdkVersion do APK: {required}. Sem adb, não foi possível ler a versão do dispositivo."}
    if device < required:
        return {"ok": False, "min_sdk": required, "device_sdk": device,
                "message": f"O dispositivo (Android API {device}) é mais antigo que o minSdk {required}; "
                           "a instalação deve ser recusada."}
    return {"ok": True, "min_sdk": required, "device_sdk": device,
            "message": f"minSdk {required} compatível com o dispositivo (API {device})."}
