from __future__ import annotations

import logging
import threading
from collections.abc import Callable

import pyautogui

from src.core.utils import AutomationStopped, ExecutionControl, countdown
from src.core.notice import (DEFAULT_NOTICE_MODE, NoticeCoordinator,
                             NoticeDidNotCloseError, NoticeMode, UnknownScreenError)
from src.core.window_detection import Win32WindowDetector
from src.flow.albergue import flujo_albergue
from src.flow.cafeteria import flujo_cafeteria
from src.flow.hotel import flujo_hotel
from src.flow.restaurante import flujo_restaurante

Flow = Callable[[int, logging.Logger, ExecutionControl], None]
FLOWS: dict[str, Flow] = {"Hotel": flujo_hotel, "Restaurante": flujo_restaurante,
                          "Cafetería": flujo_cafeteria, "Albergue": flujo_albergue}


class AutomationRunner:
    def __init__(self, emit: Callable[..., None], logger: logging.Logger) -> None:
        self.emit, self.logger = emit, logger
        self.control = ExecutionControl()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    @property
    def active(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self, caja: str, initial: int, final: int,
              notice_mode: NoticeMode = DEFAULT_NOTICE_MODE) -> bool:
        with self._lock:
            if self.active:
                return False
            self.control = ExecutionControl()
            self._thread = threading.Thread(target=self._run, args=(caja, initial, final, notice_mode),
                                            name="auto-facturas", daemon=False)
            self._thread.start()
            return True

    def toggle_pause(self) -> bool:
        if not self.active:
            return False
        if self.control.pause_event.is_set():
            self.control.pause_event.clear()
            self.emit("state", state="ejecutando", message="El proceso continúa.")
        else:
            self.control.pause_event.set()
            self.emit("state", state="pausado", message="Proceso en pausa. Pulsa Continuar cuando estés preparado.")
        return self.control.pause_event.is_set()

    def stop(self) -> None:
        self.control.stop_event.set()

    def join(self, timeout: float | None = None) -> None:
        if self._thread:
            self._thread.join(timeout)

    def _run(self, caja: str, initial: int, final: int, notice_mode: NoticeMode) -> None:
        completed, total = 0, final - initial + 1
        try:
            self.emit("state", state="cuenta atrás", message="Selecciona Fortune4 durante la cuenta atrás.")
            countdown(5, self.logger, self.control,
                      lambda value: self.emit("countdown", remaining=value))
            self.emit("state", state="ejecutando", message="Enviando la secuencia de pulsaciones.")
            notice = NoticeCoordinator(Win32WindowDetector(), self.logger)
            for number in range(initial, final + 1):
                self.emit("progress", current=number, completed=completed, total=total)
                self.logger.info("%s | FACTURA %d | INICIO", caja.upper(), number)
                if caja in {"Hotel", "Albergue"}:
                    FLOWS[caja](number, self.logger, self.control,
                                lambda: notice.handle(caja, number, notice_mode, self.control))
                else:
                    FLOWS[caja](number, self.logger, self.control)
                completed += 1
                self.logger.info("%s | FACTURA %d | FIN", caja.upper(), number)
                self.emit("progress", current=number, completed=completed, total=total)
            self.emit("finished", state="completado", message="Secuencia completada. Revisa el resultado en Fortune4.")
        except AutomationStopped:
            self.logger.warning("PROCESO DETENIDO | Solicitud del usuario.")
            self.emit("finished", state="detenido", message="El proceso se ha detenido. No se enviarán más pulsaciones.")
        except pyautogui.FailSafeException:
            self.logger.warning("PARADA DE EMERGENCIA | FailSafe activado.")
            self.emit("finished", state="detenido", message="Parada de seguridad activada. No se enviarán más pulsaciones.")
        except Exception as exc:
            self.logger.exception("ERROR INESPERADO")
            if isinstance(exc, UnknownScreenError):
                message = ("El programa ha encontrado una ventana que no reconoce y se ha detenido "
                           "para evitar errores. Revisa Fortune4 antes de volver a intentarlo.")
            elif isinstance(exc, NoticeDidNotCloseError):
                message = ("El aviso de factura contabilizada no se cerró. El proceso se ha detenido "
                           "para evitar más pulsaciones.")
            else:
                message = "El proceso se ha detenido por un problema inesperado. Revisa el registro antes de volver a intentarlo."
            self.emit("finished", state="error", message=message)
