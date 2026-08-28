from __future__ import annotations

import logging
import threading
import time
import keyboard

import pyautogui

ACTION_DELAY = 2.0
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0


def wait_if_paused(stop_event: threading.Event) -> None:
    while stop_event.is_set():
        time.sleep(0.05)


def pause(
    stop_event: threading.Event,
    seconds: float = ACTION_DELAY,
) -> None:
    remaining = seconds
    last_tick = time.monotonic()

    while remaining > 0:
        if stop_event.is_set():
            wait_if_paused(stop_event)
            last_tick = time.monotonic()
            continue

        time.sleep(min(0.05, remaining))
        now = time.monotonic()
        remaining -= now - last_tick
        last_tick = now

def write_text(
    text: str,
    description: str,
    logger: logging.Logger,
    stop_event: threading.Event,
) -> None:
    """Escribe texto, registra la acción y aplica la pausa configurada."""
    wait_if_paused(stop_event)
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
    wait_if_paused(stop_event)
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
        wait_if_paused(stop_event)
        logger.info("Inicio en %d...", remaining)
        pause(stop_event, 1)
