from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.core.notice import MODE_LABELS, NoticeMode
from src.core.persistence import VALID_CAJAS, validate_range


class AppState(str, Enum):
    READY = "preparado"
    COUNTDOWN = "cuenta atrás"
    RUNNING = "ejecutando"
    PAUSED = "pausado"
    STOPPING = "deteniendo"
    STOPPED = "detenido"
    COMPLETED = "completado"
    ERROR = "error"


@dataclass(frozen=True)
class StatePolicy:
    title: str
    color: str
    editable: bool
    can_start: bool
    can_pause: bool
    can_stop: bool
    pause_text: str = "Pausar"


STATE_POLICIES = {
    AppState.READY: StatePolicy("Preparado", "#2E7D5B", True, True, False, False),
    AppState.COUNTDOWN: StatePolicy("Cuenta atrás", "#B7791F", False, False, True, True),
    AppState.RUNNING: StatePolicy("Ejecutando", "#2563A6", False, False, True, True),
    AppState.PAUSED: StatePolicy("En pausa", "#B7791F", False, False, True, True, "Continuar"),
    AppState.STOPPING: StatePolicy("Deteniendo", "#6B7280", False, False, False, False),
    AppState.STOPPED: StatePolicy("Detenido", "#6B7280", True, True, False, False),
    AppState.COMPLETED: StatePolicy("Completado", "#2E7D5B", True, True, False, False),
    AppState.ERROR: StatePolicy("Revisar", "#B83232", True, True, False, False),
}


class FormValidationError(ValueError):
    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field


def calculate_total(initial: str, final: str) -> int | None:
    try:
        start, end = validate_range(initial, final)
    except ValueError:
        return None
    return end - start + 1


def validate_form(caja: str, initial: str, final: str,
                  mode_label: str, *, active: bool = False) -> tuple[int, int, NoticeMode]:
    if active:
        raise FormValidationError("general", "Ya hay un proceso en marcha. Deténlo antes de iniciar otro.")
    if caja not in VALID_CAJAS:
        raise FormValidationError("caja", "Selecciona una caja de la lista.")
    if not initial.strip():
        raise FormValidationError("initial", "Escribe la primera factura, por ejemplo: 260001.")
    if not final.strip():
        raise FormValidationError("final", "Escribe la última factura, por ejemplo: 260005.")
    try:
        start = int(initial)
    except ValueError as exc:
        raise FormValidationError("initial", "Introduce únicamente números, por ejemplo: 260001.") from exc
    try:
        end = int(final)
    except ValueError as exc:
        raise FormValidationError("final", "Introduce únicamente números, por ejemplo: 260005.") from exc
    if start < 0:
        raise FormValidationError("initial", "La primera factura no puede ser negativa.")
    if end < 0:
        raise FormValidationError("final", "La última factura no puede ser negativa.")
    if end < start:
        raise FormValidationError("final", "La última factura debe ser igual o posterior a la primera.")
    mode_by_label = {label: mode for mode, label in MODE_LABELS.items()}
    if caja in {"Hotel", "Albergue"} and mode_label not in mode_by_label:
        raise FormValidationError("mode", "Selecciona cómo debe comprobarse el aviso.")
    return start, end, mode_by_label.get(mode_label, NoticeMode.AUTO)


def repeats_last_settings(saved: dict | None, caja: str, initial: int, final: int,
                          mode: NoticeMode) -> bool:
    if not saved:
        return False
    if saved.get("caja") != caja or saved.get("inicial") != initial or saved.get("final") != final:
        return False
    return caja not in {"Hotel", "Albergue"} or saved.get("notice_mode") == mode.value


def shows_notice_mode(caja: str) -> bool:
    return caja in {"Hotel", "Albergue"}
