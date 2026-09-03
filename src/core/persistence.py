from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from src.core.notice import DEFAULT_NOTICE_MODE, NoticeMode

APP_NAME = "Auto-Facturas"
VALID_CAJAS = {"Hotel", "Restaurante", "Cafetería", "Albergue"}


def data_dir() -> Path:
    base = os.getenv("LOCALAPPDATA")
    return (Path(base) if base else Path.home() / ".auto-facturas") / APP_NAME


def settings_path() -> Path:
    return data_dir() / "config.json"


def validate_range(initial: str | int, final: str | int) -> tuple[int, int]:
    try:
        start, end = int(initial), int(final)
    except (TypeError, ValueError) as exc:
        raise ValueError("Las facturas deben ser números enteros no negativos.") from exc
    if start < 0 or end < 0:
        raise ValueError("Las facturas deben ser números enteros no negativos.")
    if end < start:
        raise ValueError("La factura final no puede ser menor que la inicial.")
    return start, end


def load_settings(path: Path | None = None) -> dict[str, Any] | None:
    target = path or settings_path()
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
        caja = value["caja"]
        start, end = validate_range(value["inicial"], value["final"])
        if caja not in VALID_CAJAS:
            return None
        try:
            notice_mode = NoticeMode(value.get("notice_mode", DEFAULT_NOTICE_MODE.value))
        except ValueError:
            notice_mode = DEFAULT_NOTICE_MODE
        return {"caja": caja, "inicial": start, "final": end,
                "notice_mode": notice_mode.value,
                "show_welcome": bool(value.get("show_welcome", True))}
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None


def save_settings(caja: str, initial: int, final: int,
                  show_welcome: bool = True, path: Path | None = None,
                  notice_mode: NoticeMode | str = DEFAULT_NOTICE_MODE) -> None:
    if caja not in VALID_CAJAS:
        raise ValueError("Caja no válida.")
    start, end = validate_range(initial, final)
    try:
        mode = NoticeMode(notice_mode)
    except ValueError as exc:
        raise ValueError("Modo de aviso no válido.") from exc
    target = path or settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps({"version": 2, "caja": caja, "inicial": start,
                                     "final": end, "notice_mode": mode.value,
                                     "show_welcome": show_welcome},
                                    ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(target)


def save_welcome_preference(show: bool, path: Path | None = None) -> None:
    current = load_settings(path) or {"caja": "Hotel", "inicial": 0, "final": 0}
    save_settings(current["caja"], current["inicial"], current["final"], show, path,
                  current.get("notice_mode", DEFAULT_NOTICE_MODE.value))
