from __future__ import annotations

import ctypes
from ctypes import wintypes
import re
import unicodedata
from dataclasses import dataclass

from src.core.notice import ScreenState

NOTICE_TITLE = "Fortune4 para Windows - Green Software (RED)"
NOTICE_MESSAGE = "Factura contabilizada, no deben modificarse datos económicos"
ACCEPT_TEXT = "Aceptar"
NORMAL_TITLE = "Repeticion de Facturas - REPFAC"


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(character for character in value if not unicodedata.combining(character))
    return re.sub(r"\s+", " ", value).strip().casefold()


@dataclass(frozen=True)
class WindowSnapshot:
    title: str
    texts: tuple[str, ...] = ()
    buttons: tuple[str, ...] = ()
    visible: bool = True


def classify_snapshot(snapshot: WindowSnapshot) -> ScreenState:
    if not snapshot.visible:
        return ScreenState.UNKNOWN
    title = normalize_text(snapshot.title)
    if title == normalize_text(NORMAL_TITLE):
        return ScreenState.NORMAL
    if title != normalize_text(NOTICE_TITLE):
        return ScreenState.UNKNOWN

    combined_text = normalize_text(" ".join(snapshot.texts))
    if normalize_text(NOTICE_MESSAGE) not in combined_text:
        return ScreenState.UNKNOWN
    if snapshot.buttons and normalize_text(ACCEPT_TEXT) not in {
        normalize_text(button) for button in snapshot.buttons
    }:
        return ScreenState.UNKNOWN
    return ScreenState.NOTICE


class Win32WindowDetector:
    """Clasifica la ventana activa leyendo su título y controles Win32."""

    def detect(self) -> ScreenState:
        return classify_snapshot(self.snapshot())

    def snapshot(self) -> WindowSnapshot:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.GetForegroundWindow.restype = wintypes.HWND
        user32.GetWindowTextLengthW.argtypes = (wintypes.HWND,)
        user32.GetWindowTextLengthW.restype = ctypes.c_int
        user32.GetWindowTextW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
        user32.GetWindowTextW.restype = ctypes.c_int
        user32.GetClassNameW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
        user32.GetClassNameW.restype = ctypes.c_int
        user32.IsWindowVisible.argtypes = (wintypes.HWND,)
        user32.IsWindowVisible.restype = wintypes.BOOL
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return WindowSnapshot("", visible=False)

        texts: list[str] = []
        buttons: list[str] = []
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user32.EnumChildWindows.argtypes = (wintypes.HWND, callback_type, wintypes.LPARAM)
        user32.EnumChildWindows.restype = wintypes.BOOL

        def window_text(handle: int) -> str:
            length = user32.GetWindowTextLengthW(handle)
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(handle, buffer, len(buffer))
            return buffer.value

        def class_name(handle: int) -> str:
            buffer = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(handle, buffer, len(buffer))
            return buffer.value

        @callback_type
        def collect(child: int, _param: int) -> bool:
            if user32.IsWindowVisible(child):
                text = window_text(child)
                if text:
                    texts.append(text)
                    if class_name(child).casefold() == "button":
                        buttons.append(text)
            return True

        user32.EnumChildWindows(hwnd, collect, 0)
        return WindowSnapshot(window_text(hwnd), tuple(texts), tuple(buttons),
                              bool(user32.IsWindowVisible(hwnd)))
