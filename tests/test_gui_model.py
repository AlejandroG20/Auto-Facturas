import logging
import queue
import unittest
from unittest.mock import Mock, patch

from src.gui.app import AutoFacturasApp, QueueLogHandler
from src.gui.model import (AppState, FormValidationError, STATE_POLICIES,
                           calculate_total, repeats_last_settings,
                           validate_form)


class GuiModelTests(unittest.TestCase):
    def test_total_includes_both_ends(self):
        self.assertEqual(calculate_total("260002", "260005"), 4)
        self.assertEqual(calculate_total("7", "7"), 1)
        self.assertIsNone(calculate_total("x", "8"))
        self.assertIsNone(calculate_total("9", "8"))

    def test_form_validation_returns_clear_field_errors(self):
        cases = (
            (("Hotel", "", "2"), "initial"),
            (("Hotel", "x", "2"), "initial"),
            (("Hotel", "1", ""), "final"),
            (("Hotel", "3", "2"), "final"),
            (("Otra", "1", "2"), "caja"),
        )
        for arguments, field in cases:
            with self.subTest(field=field), self.assertRaises(FormValidationError) as raised:
                validate_form(*arguments)
            self.assertEqual(raised.exception.field, field)
            self.assertNotIn("ValueError", str(raised.exception))

    def test_active_process_cannot_start_again(self):
        with self.assertRaises(FormValidationError) as raised:
            validate_form("Hotel", "1", "2", active=True)
        self.assertEqual(raised.exception.field, "general")

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
                 "notice_mode": "antiguas"}
        self.assertTrue(repeats_last_settings(saved, "Hotel", 1, 3))
        self.assertFalse(repeats_last_settings(saved, "Hotel", 1, 4))
        self.assertTrue(repeats_last_settings(saved, "Hotel", 1, 3))

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


class YearFormTests(unittest.TestCase):
    def make_form(self, caja, ano):
        app = Mock()
        app.caja.get.return_value = caja
        app.initial.get.return_value = "7"
        app.final.get.return_value = "9"
        app.ano.get.return_value = ano
        app.runner.active = False
        return app

    def test_year_required_before_start(self):
        for caja in ("Hotel", "Albergue"):
            for ano in ("", "2021", "x1"):
                app = self.make_form(caja, ano)
                with patch("src.gui.app.load_settings", return_value=None), patch("src.gui.app.save_settings") as save:
                    AutoFacturasApp._start(app)
                app.runner.start.assert_not_called()
                save.assert_not_called()
                app.ano.focus_set.assert_called_once()

    def test_form_passes_year_to_runner(self):
        for caja in ("Hotel", "Albergue", "Restaurante", "Cafeter\u00eda"):
            app = self.make_form(caja, "19")
            with patch("src.gui.app.load_settings", return_value=None), patch("src.gui.app.save_settings"):
                AutoFacturasApp._start(app)
            app.runner.start.assert_called_once_with(caja, 7, 9, ano="19" if caja in ("Hotel", "Albergue") else None)

    def test_pause_hotkey_is_f10(self):
        app = Mock()
        with patch("src.gui.app.keyboard.on_release_key") as register:
            AutoFacturasApp._register_hotkey(app)
        register.assert_called_once_with("f10", app._hotkey_toggle, suppress=True)
