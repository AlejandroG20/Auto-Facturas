from __future__ import annotations

import logging
from collections.abc import Callable
from enum import Enum
from typing import Protocol

from src.core.utils import ExecutionControl, pause, press_key


class NoticeMode(str, Enum):
    OLD = "antiguas"
    MODERN = "modernas"
    AUTO = "automatico"


MODE_LABELS = {
    NoticeMode.OLD: "Facturas antiguas",
    NoticeMode.MODERN: "Facturas modernas",
    NoticeMode.AUTO: "Detección automática",
}
DEFAULT_NOTICE_MODE = NoticeMode.AUTO


class ScreenState(str, Enum):
    NOTICE = "notice"
    NORMAL = "normal"
    UNKNOWN = "unknown"


class ScreenDetector(Protocol):
    def detect(self) -> ScreenState: ...


class NoticeError(RuntimeError):
    """Error seguro al reconocer o cerrar el aviso de Fortune4."""


class UnknownScreenError(NoticeError):
    pass


class NoticeDidNotCloseError(NoticeError):
    pass


class NoticeCoordinator:
    def __init__(
        self,
        detector: ScreenDetector,
        logger: logging.Logger,
        *,
        detection_timeout: float = 2.0,
        close_timeout: float = 2.0,
        poll_interval: float = 0.1,
        normal_confirmations: int = 2,
        accept: Callable[[logging.Logger, ExecutionControl], None] | None = None,
    ) -> None:
        self.detector = detector
        self.logger = logger
        self.detection_timeout = detection_timeout
        self.close_timeout = close_timeout
        self.poll_interval = poll_interval
        self.normal_confirmations = normal_confirmations
        self.accept = accept or self._press_enter

    @staticmethod
    def _press_enter(logger: logging.Logger, control: ExecutionControl) -> None:
        press_key("enter", "Aceptar aviso de factura contabilizada", logger, control)

    def handle(self, caja: str, number: int, mode: NoticeMode,
               control: ExecutionControl) -> None:
        prefix = f"{caja.upper()} | Factura {number}"
        remaining = self.detection_timeout
        normal_seen = 0
        while True:
            control.wait_if_paused()
            state = self.detector.detect()
            if state is ScreenState.NOTICE:
                self.accept(self.logger, control)
                self._verify_closed(prefix, control)
                if mode is NoticeMode.MODERN:
                    self.logger.info("%s | Modo modernas | Aviso inesperado detectado y aceptado", prefix)
                else:
                    self.logger.info("%s | Aviso de factura contabilizada detectado y aceptado", prefix)
                return
            if state is ScreenState.NORMAL:
                normal_seen += 1
                if normal_seen >= self.normal_confirmations:
                    if mode is NoticeMode.OLD:
                        self.logger.info("%s | Modo antiguas | Aviso no mostrado; continúa el flujo normal", prefix)
                    else:
                        self.logger.info("%s | Aviso no mostrado; continúa el flujo normal", prefix)
                    return
            else:
                normal_seen = 0
            if remaining <= 0:
                message = f"{prefix} | Pantalla desconocida; automatización detenida"
                self.logger.error(message)
                raise UnknownScreenError(message)
            pause(control, self.poll_interval)
            remaining -= self.poll_interval

    def _verify_closed(self, prefix: str, control: ExecutionControl) -> None:
        remaining = self.close_timeout
        while True:
            control.wait_if_paused()
            state = self.detector.detect()
            if state is ScreenState.NORMAL:
                return
            if remaining <= 0:
                message = f"{prefix} | El aviso no desapareció tras aceptarlo; automatización detenida"
                self.logger.error(message)
                raise NoticeDidNotCloseError(message)
            pause(control, self.poll_interval)
            remaining -= self.poll_interval
