import logging
import threading
from collections.abc import Callable

from src.core.utils import enter_times, press_key, write_text


def flujo_albergue(numero: int, logger: logging.Logger, stop_event: threading.Event,
                   check_notice: Callable[[], None] | None = None) -> None:
    """Introduce el número y la referencia siguiendo la secuencia de Albergue."""
    write_text(str(numero), "Número de factura", logger, stop_event)
    enter_times(4, logger, stop_event)
    if check_notice:
        check_notice()
    press_key("f12", "F12", logger, stop_event)
    enter_times(0, logger, stop_event)
    write_text(f"FRA {numero}", "Referencia", logger, stop_event)
    press_key("enter", "Enter final", logger, stop_event)
