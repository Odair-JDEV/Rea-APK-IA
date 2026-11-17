"""Histórico de builds e estado por APK.

Dois arquivos JSON, sempre fora do APK original:

- `builds/history.json`: uma linha por reconstrução (data, duração, etapas, resultado, SHA-256).
- `output/<app>_apktool/.readroid.json`: estado daquela pasta decodificada (APK de origem,
  SHA-256, data da extração, edições aplicadas, último build).

Nada aqui executa comandos ou altera o APK; é só registro.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MAX_HISTORY_ENTRIES = 200
STATE_FILE = ".readroid.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_json(path: Path, default: Any) -> Any:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default
    return data if isinstance(data, type(default)) else default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


# ------------------------------------------------------------------ histórico de builds

def history_path(builds_dir: Path) -> Path:
    return builds_dir / "history.json"


def load_history(builds_dir: Path) -> list[dict[str, Any]]:
    data = _read_json(history_path(builds_dir), [])
    return [item for item in data if isinstance(item, dict)]


def record_build(builds_dir: Path, result: dict[str, Any], decoded: Path,
                 started_at: str | None = None, duration_s: float | None = None) -> dict[str, Any]:
    """Acrescenta uma entrada ao histórico e devolve a entrada gravada."""
    steps = result.get("steps", {}) or {}
    entry = {
        "at": _now(),
        "started_at": started_at,
        "duration_s": round(duration_s, 1) if duration_s is not None else None,
        "decoded": decoded.name,
        "ok": bool(result.get("ok")),
        "final_apk": result.get("final_apk"),
        "sha256": steps.get("sha256"),
        "steps": {name: {"ok": step.get("ok"), "skipped": bool(step.get("skipped"))}
                  for name, step in steps.items() if isinstance(step, dict)},
    }
    history = load_history(builds_dir)
    history.append(entry)
    _write_json(history_path(builds_dir), history[-MAX_HISTORY_ENTRIES:])
    return entry


def format_history(entries: list[dict[str, Any]], limit: int = 15) -> list[str]:
    """Linhas prontas para o terminal, do mais recente para o mais antigo."""
    lines: list[str] = []
    for entry in reversed(entries[-limit:]):
        mark = "OK" if entry.get("ok") else "falhou"
        when = str(entry.get("at", ""))[:19].replace("T", " ")
        duration = entry.get("duration_s")
        took = f" · {duration}s" if duration is not None else ""
        apk = Path(str(entry.get("final_apk") or "")).name or "-"
        lines.append(f"{when} · {entry.get('decoded', '?')} · {mark}{took} · {apk}")
    return lines


# ------------------------------------------------------------------ estado por APK

def state_path(decoded: Path) -> Path:
    return decoded / STATE_FILE


def load_state(decoded: Path) -> dict[str, Any]:
    return _read_json(state_path(decoded), {})


def save_state(decoded: Path, patch: dict[str, Any]) -> dict[str, Any]:
    state = load_state(decoded)
    state.update(patch)
    state["updated_at"] = _now()
    _write_json(state_path(decoded), state)
    return state


def mark_extracted(decoded: Path, apk: Path, sha256: str | None = None) -> dict[str, Any]:
    return save_state(decoded, {
        "source_apk": apk.name,
        "source_path": str(apk),
        "source_sha256": sha256,
        "extracted_at": _now(),
        "edits": [],
    })


def add_edit(decoded: Path, description: str) -> dict[str, Any]:
    state = load_state(decoded)
    edits = state.get("edits")
    if not isinstance(edits, list):
        edits = []
    edits.append({"at": _now(), "what": description})
    return save_state(decoded, {"edits": edits[-100:]})


def mark_build(decoded: Path, entry: dict[str, Any]) -> dict[str, Any]:
    return save_state(decoded, {"last_build": entry})
