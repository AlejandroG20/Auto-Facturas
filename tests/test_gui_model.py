import logging
import queue
import unittest

from src.core.notice import MODE_LABELS, NoticeMode
from src.gui.app import QueueLogHandler
from src.gui.model import (AppState, FormValidationError, STATE_POLICIES,
                           calculate_total, repeats_last_settings,
                           shows_notice_mode, validate_form)


class GuiModelTests(unittest.TestCase):
    def test_total_includes_both_ends(self):
        self.assertEqual(calculate_total("260002", "260005"), 4)
        self.assertEqual(calculate_total("7", "7"), 1)
        self.assertIsNone(calculate_total("x", "8"))
        self.assertIsNone(calculate_total("9", "8"))

    def test_form_validation_returns_clear_field_errors(self):
        cases = (
            (("Hotel", "", "2", MODE_LABELS[NoticeMode.AUTO]), "initial"),
            (("Hotel", "x", "2", MODE_LABELS[NoticeMode.AUTO]), "initial"),
            (("Hotel", "1", "", MODE_LABELS[NoticeMode.AUTO]), "final"),
            (("Hotel", "3", "2", MODE_LABELS[NoticeMode.AUTO]), "final"),
            (("Otra", "1", "2", MODE_LABELS[NoticeMode.AUTO]), "caja"),
            (("Hotel", "1", "2", ""), "mode"),
        )
        for arguments, field in cases:
            with self.subTest(field=field), self.assertRaises(FormValidationError) as raised:
                validate_form(*arguments)
            self.assertEqual(raised.exception.field, field)
            self.assertNotIn("ValueError", str(raised.exception))

    def test_active_process_cannot_start_again(self):
        with self.assertRaises(FormValidationError) as raised:
            validate_form("Hotel", "1", "2", MODE_LABELS[NoticeMode.AUTO], active=True)
        self.assertEqual(raised.exception.field, "general")

    def test_notice_mode_visibility_depends_on_caja(self):
        self.assertTrue(shows_notice_mode("Hotel"))
        self.assertTrue(shows_notice_mode("Albergue"))
        self.assertFalse(shows_notice_mode("Restaurante"))
        self.assertFalse(shows_notice_mode("Cafetería"))

    def test_all_interface_states_have_consistent_controls(self):
        self.assertEqual(set(STATE_POLICIES), set(AppState))
        for state in (AppState.COUNTDOWN, AppState.RUNNING, AppState.PAUSED):
            policy = STATE_POLICIES[state]
            self.assertFalse(policy.editable)
            self.assertFalse(policy.can_start)
            self.assertTrue(policy.can_stop)
        self.assertEqual(STATE_POLICIES[AppState.PAUSED].pause_text, "Continuar")
        self.assertFalse(STATE_POLICIES[AppState.STOPPING].can_stop)

    def test_repeat_warning_only_matches_exact_configuration(self):
        saved = {"caja": "Hotel", "inicial": 1, "final": 3,
                 "notice_mode": NoticeMode.AUTO.value}
        self.assertTrue(repeats_last_settings(saved, "Hotel", 1, 3, NoticeMode.AUTO))
        self.assertFalse(repeats_last_settings(saved, "Hotel", 1, 4, NoticeMode.AUTO))
        self.assertFalse(repeats_last_settings(saved, "Hotel", 1, 3, NoticeMode.OLD))

    def test_worker_logs_are_queued_with_their_level(self):
        events = queue.Queue()
        handler = QueueLogHandler(events)
        record = logging.LogRecord("test", logging.ERROR, "", 0, "Problema", (), None)
        handler.emit(record)
        kind, data = events.get_nowait()
        self.assertEqual(kind, "log")
        self.assertEqual(data["level"], logging.ERROR)


if __name__ == "__main__":
    unittest.main()
