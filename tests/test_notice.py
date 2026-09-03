import logging
import threading
import time
import unittest

from src.core.notice import (
    NoticeCoordinator,
    NoticeDidNotCloseError,
    NoticeMode,
    ScreenState,
    UnknownScreenError,
)
from src.core.utils import AutomationStopped, ExecutionControl
from src.core.window_detection import NOTICE_MESSAGE, NOTICE_TITLE, WindowSnapshot, classify_snapshot


class SequenceDetector:
    def __init__(self, states):
        self.states = list(states)
        self.last = self.states[-1]

    def detect(self):
        if self.states:
            self.last = self.states.pop(0)
        return self.last


def coordinator(states, accepted, **kwargs):
    return NoticeCoordinator(
        SequenceDetector(states),
        logging.getLogger("notice-test"),
        detection_timeout=kwargs.pop("detection_timeout", .05),
        close_timeout=kwargs.pop("close_timeout", .05),
        poll_interval=.001,
        normal_confirmations=1,
        accept=lambda _logger, _control: accepted.append("enter"),
        **kwargs,
    )


class WindowClassificationTests(unittest.TestCase):
    def test_notice_tolerates_case_accents_spacing_and_line_breaks(self):
        snapshot = WindowSnapshot(
            NOTICE_TITLE,
            ("FACTURA   CONTABILIZADA,\nno deben modificarse datos economicos", "Aceptar"),
            ("ACEPTAR",),
        )
        self.assertIs(classify_snapshot(snapshot), ScreenState.NOTICE)

    def test_different_fortune_alert_is_unknown(self):
        snapshot = WindowSnapshot(NOTICE_TITLE, ("La factura no existe", "Aceptar"), ("Aceptar",))
        self.assertIs(classify_snapshot(snapshot), ScreenState.UNKNOWN)

    def test_notice_with_different_readable_button_is_unknown(self):
        snapshot = WindowSnapshot(NOTICE_TITLE, (NOTICE_MESSAGE, "Cancelar"), ("Cancelar",))
        self.assertIs(classify_snapshot(snapshot), ScreenState.UNKNOWN)

    def test_repfac_is_normal(self):
        self.assertIs(
            classify_snapshot(WindowSnapshot("Repeticion de Facturas - REPFAC")),
            ScreenState.NORMAL,
        )


class NoticeCoordinatorTests(unittest.TestCase):
    def test_hotel_old_with_notice_accepts_once(self):
        accepted = []
        coordinator([ScreenState.NOTICE, ScreenState.NORMAL], accepted).handle(
            "Hotel", 260001, NoticeMode.OLD, ExecutionControl())
        self.assertEqual(accepted, ["enter"])

    def test_hotel_old_without_notice_continues(self):
        accepted = []
        coordinator([ScreenState.NORMAL], accepted).handle(
            "Hotel", 260002, NoticeMode.OLD, ExecutionControl())
        self.assertEqual(accepted, [])

    def test_hotel_modern_without_notice_continues(self):
        accepted = []
        coordinator([ScreenState.NORMAL], accepted).handle(
            "Hotel", 260003, NoticeMode.MODERN, ExecutionControl())
        self.assertEqual(accepted, [])

    def test_hotel_modern_accepts_unexpected_notice(self):
        accepted = []
        coordinator([ScreenState.NOTICE, ScreenState.NORMAL], accepted).handle(
            "Hotel", 260004, NoticeMode.MODERN, ExecutionControl())
        self.assertEqual(accepted, ["enter"])

    def test_albergue_modes_with_and_without_notice(self):
        for mode, states, expected in (
            (NoticeMode.OLD, [ScreenState.NOTICE, ScreenState.NORMAL], ["enter"]),
            (NoticeMode.MODERN, [ScreenState.NORMAL], []),
            (NoticeMode.AUTO, [ScreenState.NOTICE, ScreenState.NORMAL], ["enter"]),
            (NoticeMode.AUTO, [ScreenState.NORMAL], []),
        ):
            with self.subTest(mode=mode, states=states):
                accepted = []
                coordinator(states, accepted).handle("Albergue", 260005, mode, ExecutionControl())
                self.assertEqual(accepted, expected)

    def test_unknown_screen_stops_safely(self):
        with self.assertRaises(UnknownScreenError):
            coordinator([ScreenState.UNKNOWN], [], detection_timeout=.005).handle(
                "Hotel", 1, NoticeMode.AUTO, ExecutionControl())

    def test_notice_that_does_not_close_stops_safely(self):
        accepted = []
        with self.assertRaises(NoticeDidNotCloseError):
            coordinator([ScreenState.NOTICE], accepted, close_timeout=.005).handle(
                "Hotel", 1, NoticeMode.AUTO, ExecutionControl())
        self.assertEqual(accepted, ["enter"])

    def test_pause_and_resume_during_detection(self):
        accepted = []
        control = ExecutionControl()
        control.pause_event.set()
        result = []
        worker = threading.Thread(target=lambda: (
            coordinator([ScreenState.NORMAL], accepted).handle(
                "Hotel", 1, NoticeMode.AUTO, control), result.append("done")))
        worker.start()
        time.sleep(.02)
        self.assertEqual(result, [])
        control.pause_event.clear()
        worker.join(1)
        self.assertEqual(result, ["done"])

    def test_stop_during_detection(self):
        control = ExecutionControl()
        worker_result = []

        def run():
            try:
                coordinator([ScreenState.UNKNOWN], [], detection_timeout=1).handle(
                    "Hotel", 1, NoticeMode.AUTO, control)
            except AutomationStopped:
                worker_result.append("stopped")

        worker = threading.Thread(target=run)
        worker.start()
        time.sleep(.02)
        control.stop_event.set()
        worker.join(1)
        self.assertEqual(worker_result, ["stopped"])


if __name__ == "__main__":
    unittest.main()
