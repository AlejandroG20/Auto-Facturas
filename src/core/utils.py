from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field

import keyboard
import pyautogui

ACTION_DELAY = 2.0
CHAR_DELAY = 0.05
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0


class AutomationStopped(Exception):
    """Parada ordenada solicitada por el usuario."""


@dataclass
class ExecutionControl:
    pause_event: threading.Event = field(default_factory=threading.Event)
    stop_event: threading.Event = field(default_factory=threading.Event)

    def check(self) -> None:
        if self.stop_event.is_set():
            raise AutomationStopped

    def wait_if_paused(self) -> None:
        self.check()
        while self.pause_event.is_set():
            if self.stop_event.wait(0.05):
                raise AutomationStopped


def _control(value: ExecutionControl | threading.Event) -> ExecutionControl:
    if isinstance(value, ExecutionControl):
        return value
    return ExecutionControl(pause_event=value)


def _check_failsafe() -> None:
    """Extiende el FailSafe a las acciones escritas mediante keyboard."""
    if pyautogui.FAILSAFE and tuple(pyautogui.position()) in pyautogui.FAILSAFE_POINTS:
        raise pyautogui.FailSafeException


def wait_if_paused(control: ExecutionControl | threading.Event) -> None:
    _control(control).wait_if_paused()


def pause(control: ExecutionControl | threading.Event, seconds: float = ACTION_DELAY) -> None:
    ctl = _control(control)
    remaining = seconds
    last_tick = time.monotonic()
    while remaining > 0:
        ctl.wait_if_paused()
        if ctl.stop_event.wait(min(0.05, remaining)):
            raise AutomationStopped
        now = time.monotonic()
        remaining -= now - last_tick
        last_tick = now


def write_text(text: str, description: str, logger: logging.Logger,
               control: ExecutionControl | threading.Event) -> None:
    """Escribe sin perder la posición si se pausa entre caracteres."""
    ctl = _control(control)
    logger.info("[TEXTO] %s: %s", description, text)
    for character in text:
        ctl.wait_if_paused()
        _check_failsafe()
        keyboard.write(character)
        pause(ctl, CHAR_DELAY)
    pause(ctl)


def press_key(key: str, description: str, logger: logging.Logger,
              control: ExecutionControl | threading.Event) -> None:
    ctl = _control(control)
    ctl.wait_if_paused()
    logger.info("[TECLA] %s", description)
    pyautogui.press(key)
    pause(ctl)


def enter_times(times: int, logger: logging.Logger,
                control: ExecutionControl | threading.Event) -> None:
    for index in range(1, times + 1):
        press_key("enter", f"Enter #{index}", logger, control)


def countdown(seconds: int, logger: logging.Logger,
              control: ExecutionControl | threading.Event, on_tick=None) -> None:
    ctl = _control(control)
    logger.info("Cambia ahora a la ventana del programa de facturación.")
    for remaining in range(seconds, 0, -1):
        ctl.wait_if_paused()
        if on_tick:
            on_tick(remaining)
        logger.info("Inicio en %d...", remaining)
        pause(ctl, 1)
