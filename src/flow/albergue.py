import logging
import threading

from src.core.utils import enter_times, press_key, write_text


def flujo_albergue(numero: int, logger: logging.Logger, stop_event: threading.Event) -> None:
    """Introduce el número y la referencia siguiendo la secuencia de Albergue."""
    write_text(str(numero), "Número de factura", logger, stop_event)
    enter_times(4, logger, stop_event)
    press_key("f12", "F12", logger, stop_event)
    enter_times(2, logger, stop_event)
    write_text(f"FRA{numero}", "Referencia", logger, stop_event)
    press_key("enter", "Enter final", logger, stop_event)
