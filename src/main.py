from __future__ import annotations

import logging
import threading
from collections.abc import Callable

import keyboard
import pyautogui

from src.core.logs import setup_logger
from src.core.utils import countdown
from src.flow.albergue import flujo_albergue
from src.flow.cafeteria import flujo_cafeteria
from src.flow.hotel import flujo_hotel
from src.flow.restaurante import flujo_restaurante

Flow = Callable[[int, logging.Logger, threading.Event], None]

CAJAS: dict[str, tuple[str, Flow]] = {
    "1": ("HOTEL", flujo_hotel),
    "2": ("RESTAURANTE", flujo_restaurante),
    "3": ("CAFETERÍA", flujo_cafeteria),
    "4": ("ALBERGUE", flujo_albergue),
}


def seleccionar_caja() -> tuple[str, Flow]:
    print("\nSelecciona la caja:\n")
    print("1) Hotel")
    print("2) Restaurante")
    print("3) Cafetería")
    print("4) Albergue\n")

    while True:
        opcion = input("Opción: ").strip()

        if opcion in CAJAS:
            return CAJAS[opcion]

        print("Opción no válida. Escribe un número del 1 al 4.")


def solicitar_entero(mensaje: str) -> int:
    while True:
        value = input(mensaje).strip()

        try:
            number = int(value)

            if number < 0:
                raise ValueError

            return number

        except ValueError:
            print("Introduce un número entero igual o mayor que 0.")


def main() -> None:
    logger, log_path = setup_logger()
    pause_event = threading.Event()
    hotkey_registered = False

    logger.info("=== NUEVA SESIÓN DE FACTURAS ===")
    logger.info("Log: %s", log_path)

    try:
        caja, flow = seleccionar_caja()
        inicial = solicitar_entero("Número de factura INICIAL: ")
        final = solicitar_entero("Número de factura FINAL: ")

        while final < inicial:
            print("La factura final no puede ser menor que la inicial.")
            final = solicitar_entero("Número de factura FINAL: ")

        logger.info(
            "Caja: %s | Rango: %d-%d | Total: %d",
            caja,
            inicial,
            final,
            final - inicial + 1,
        )

        print("\nPulsa / para pausar y vuelve a pulsar / para continuar.")

        def toggle_pause() -> None:
            if pause_event.is_set():
                pause_event.clear()
                logger.info("PROCESO REANUDADO")
            else:
                pause_event.set()
                logger.warning(
                    "PROCESO EN PAUSA | Pulsa / para continuar."
                )

        keyboard.add_hotkey(
            "/",
            toggle_pause,
            suppress=True,
            trigger_on_release=True,
        )
        hotkey_registered = True

        countdown(5, logger, pause_event)

        completed = 0

        for numero in range(inicial, final + 1):
            logger.info("%s | FACTURA %d | INICIO", caja, numero)

            flow(numero, logger, pause_event)

            completed += 1
            logger.info("%s | FACTURA %d | FIN", caja, numero)

        logger.info(
            "PROCESO COMPLETADO | Facturas procesadas: %d",
            completed,
        )

    except pyautogui.FailSafeException:
        logger.warning(
            "PARADA DE EMERGENCIA | FailSafe de PyAutoGUI activado."
        )

    except KeyboardInterrupt:
        logger.warning(
            "PROCESO DETENIDO | Interrupción desde la consola."
        )

    except Exception:
        logger.exception("ERROR INESPERADO")

    finally:
        if hotkey_registered:
            keyboard.unhook_all_hotkeys()

        logger.info("=== FIN DE LA SESIÓN ===")


if __name__ == "__main__":
    main()
