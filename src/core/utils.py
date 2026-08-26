from __future__ import annotations

import logging
import threading
import time
import keyboard

import pyautogui

ACTION_DELAY = 2.0
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0


class StopRequested(Exception):
    """Raised when the user requests a controlled stop."""


def check_stop(stop_event: threading.Event) -> None:
    """Interrumpe el flujo si el usuario ha solicitado una parada manual."""
    if stop_event.is_set():
        raise StopRequested("Parada manual solicitada con la tecla H.")


def pause(stop_event: threading.Event, seconds: float = ACTION_DELAY) -> None:
    """Espera entre acciones sin dejar de responder a la tecla de parada."""
    if stop_event.wait(seconds):
        raise StopRequested("Parada manual solicitada con la tecla H.")


def write_text(
    text: str,
    description: str,
    logger: logging.Logger,
    stop_event: threading.Event,
) -> None:
    """Escribe texto, registra la acción y aplica la pausa configurada."""
    check_stop(stop_event)
    logger.info("[TEXTO] %s: %s", description, text)

    keyboard.write(text, delay=0.05)

    pause(stop_event)

def press_key(
    key: str,
    description: str,
    logger: logging.Logger,
    stop_event: threading.Event,
) -> None:
    """Pulsa una tecla, registra la acción y aplica la pausa configurada."""
    check_stop(stop_event)
    logger.info("[TECLA] %s", description)
    pyautogui.press(key)
    pause(stop_event)


def enter_times(
    times: int,
    logger: logging.Logger,
    stop_event: threading.Event,
) -> None:
    """Pulsa Enter el número de veces indicado."""
    for index in range(1, times + 1):
        press_key("enter", f"Enter #{index}", logger, stop_event)


def countdown(
    seconds: int,
    logger: logging.Logger,
    stop_event: threading.Event,
) -> None:
    """Da tiempo para cambiar de ventana antes de iniciar la automatización."""
    logger.info("Cambia ahora a la ventana del programa de facturación.")
    for remaining in range(seconds, 0, -1):
        check_stop(stop_event)
        logger.info("Inicio en %d...", remaining)
        if stop_event.wait(1):
            raise StopRequested("Parada solicitada durante la cuenta atrás.")
