from __future__ import annotations

import logging
from enum import Enum

from src.core.utils import ExecutionControl, press_key


class NoticeMode(str, Enum):
    OLD = "antiguas"
    MODERN = "modernas"


MODE_LABELS = {
    NoticeMode.OLD: "Facturas antiguas",
    NoticeMode.MODERN: "Facturas modernas",
}
DEFAULT_NOTICE_MODE = NoticeMode.MODERN


class NoticeCoordinator:
    """Aplica la selección manual sin inspeccionar la ventana activa."""

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    def handle(self, caja: str, number: int, mode: NoticeMode,
               control: ExecutionControl) -> None:
        mode = NoticeMode(mode)
        control.wait_if_paused()
        if mode is NoticeMode.OLD:
            press_key("enter", "Aceptar aviso de factura contabilizada", self.logger, control)
        self.logger.info("%s | Factura %d | Tipo seleccionado: %s",
                         caja.upper(), number, MODE_LABELS[mode])
