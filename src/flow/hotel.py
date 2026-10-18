import logging
import threading
from collections.abc import Callable

from src.core.utils import enter_times, press_key, write_text


def flujo_hotel(numero: int, logger: logging.Logger, stop_event: threading.Event,
                check_notice: Callable[[], None] | None = None, *, ano: str) -> None:
    """Introduce el número y la referencia siguiendo la secuencia de Hotel."""
    if len(ano) != 2 or not ano.isascii() or not ano.isdigit():
        raise ValueError("El año debe tener dos cifras, por ejemplo: 19, 20 o 21.")
    write_text(str(numero), "Número de factura", logger, stop_event)
    enter_times(1, logger, stop_event)
    write_text(ano, "Año", logger, stop_event)
    enter_times(2, logger, stop_event)
    press_key("f12", "F12", logger, stop_event)
    enter_times(0, logger, stop_event)
    write_text(f"FRA {numero}", "Referencia", logger, stop_event)
    press_key("enter", "Enter final", logger, stop_event)
