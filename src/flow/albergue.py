import logging
import threading
from collections.abc import Callable

from src.core.utils import enter_times, press_key, write_text


def flujo_albergue(numero: int, logger: logging.Logger, stop_event: threading.Event,
                   check_notice: Callable[[], None] | None = None, *, ano: str) -> None:
    if len(ano) != 2 or not ano.isascii() or not ano.isdigit():
        raise ValueError("El año debe tener dos cifras, por ejemplo: 19, 20 o 21.")
    write_text(str(numero), "Número de factura", logger, stop_event)
    enter_times(1, logger, stop_event)
    write_text(ano, "Año", logger, stop_event)
    enter_times(3, logger, stop_event)
    press_key("f12", "F12", logger, stop_event)
    enter_times(1, logger, stop_event)
    write_text(f"FRA {numero}", "Referencia", logger, stop_event)
    press_key("enter", "Enter final", logger, stop_event)
