import json
import logging
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from src.core.persistence import load_settings, save_settings, save_welcome_preference, validate_range
from src.core.notice import DEFAULT_NOTICE_MODE, NoticeMode
from src.core.runner import AutomationRunner, FLOWS
from src.core.utils import AutomationStopped, ExecutionControl, pause


class PersistenceTests(unittest.TestCase):
    def test_ranges(self):
        self.assertEqual(validate_range("2", "5"), (2, 5))
        for values in (("x", "2"), ("-1", "2"), ("3", "2")):
            with self.assertRaises(ValueError): validate_range(*values)

    def test_save_load_and_welcome(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "config.json"
            save_settings("Hotel", 260002, 260005, path=path)
            self.assertEqual(load_settings(path)["final"], 260005)
            self.assertEqual(load_settings(path)["notice_mode"], DEFAULT_NOTICE_MODE.value)
            save_welcome_preference(False, path)
            self.assertFalse(load_settings(path)["show_welcome"])

    def test_invalid_files(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "config.json"
            self.assertIsNone(load_settings(path))
            path.write_text("{broken", encoding="utf-8")
            self.assertIsNone(load_settings(path))
            path.write_text(json.dumps({"caja": "Otra", "inicial": 1, "final": 2}), encoding="utf-8")
            self.assertIsNone(load_settings(path))

    def test_old_settings_without_notice_mode_are_compatible(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "config.json"
            path.write_text(json.dumps({"version": 1, "caja": "Hotel", "inicial": 1,
                                        "final": 2, "show_welcome": True}), encoding="utf-8")
            self.assertEqual(load_settings(path)["notice_mode"], DEFAULT_NOTICE_MODE.value)
            save_settings("Albergue", 1, 2, path=path, notice_mode=NoticeMode.OLD)
            self.assertEqual(load_settings(path)["notice_mode"], NoticeMode.OLD.value)


class ControlTests(unittest.TestCase):
    def test_stop_works_while_paused(self):
        ctl = ExecutionControl(); ctl.pause_event.set()
        result = []
        thread = threading.Thread(target=lambda: self._capture_stop(ctl, result)); thread.start()
        time.sleep(.03); ctl.stop_event.set(); thread.join(1)
        self.assertEqual(result, ["stopped"])

    @staticmethod
    def _capture_stop(ctl, result):
        try: pause(ctl, 1)
        except AutomationStopped: result.append("stopped")

    def test_pause_preserves_remaining_wait(self):
        ctl = ExecutionControl(); started = time.monotonic()
        thread = threading.Thread(target=pause, args=(ctl, .12)); thread.start()
        time.sleep(.04); ctl.pause_event.set(); time.sleep(.1); ctl.pause_event.clear(); thread.join()
        self.assertGreaterEqual(time.monotonic() - started, .20)


class FlowSequenceTests(unittest.TestCase):
    EXPECTED = {
        "Hotel": [("write", "7"), ("enter", 4), ("press", "f12"), ("enter", 0), ("write", "FRA 7"), ("press", "enter")],
        "Albergue": [("write", "7"), ("enter", 4), ("press", "f12"), ("enter", 0), ("write", "FRA 7"), ("press", "enter")],
        "Restaurante": [("enter", 3), ("write", "7"), ("press", "f12"), ("press", "enter"), ("write", "FRA 7"), ("press", "enter")],
        "Cafetería": [("enter", 3), ("write", "7"), ("press", "f12"), ("press", "enter"), ("write", "FRA 7"), ("press", "enter")],
    }
    def test_sequences_are_preserved(self):
        for name, flow in FLOWS.items():
            calls = []; module = flow.__module__
            with patch(f"{module}.write_text", side_effect=lambda text, *_: calls.append(("write", text))), patch(f"{module}.enter_times", side_effect=lambda count, *_: calls.append(("enter", count))), patch(f"{module}.press_key", side_effect=lambda key, *_: calls.append(("press", key))):
                flow(7, logging.getLogger("test"), ExecutionControl())
            self.assertEqual(calls, self.EXPECTED[name])

    def test_notice_check_is_inserted_between_initial_enters_and_f12(self):
        for name in ("Hotel", "Albergue"):
            flow = FLOWS[name]
            calls = []
            module = flow.__module__
            with patch(f"{module}.write_text", side_effect=lambda text, *_: calls.append(("write", text))), \
                    patch(f"{module}.enter_times", side_effect=lambda count, *_: calls.append(("enter", count))), \
                    patch(f"{module}.press_key", side_effect=lambda key, *_: calls.append(("press", key))):
                flow(7, logging.getLogger("test"), ExecutionControl(),
                     lambda: calls.append(("notice", None)))
            self.assertEqual(calls[2:4], [("notice", None), ("press", "f12")])


class RunnerTests(unittest.TestCase):
    def test_prevents_simultaneous_runs_and_stops_countdown(self):
        events = []; logger = logging.getLogger("runner-test")
        runner = AutomationRunner(lambda kind, **data: events.append((kind, data)), logger)
        with patch("src.core.runner.countdown", side_effect=lambda _s, _l, ctl, _cb: ctl.stop_event.wait(.3) and (_ for _ in ()).throw(AutomationStopped())):
            self.assertTrue(runner.start("Hotel", 1, 1)); self.assertFalse(runner.start("Hotel", 1, 1))
            runner.stop(); runner.join(1)
        self.assertTrue(any(data.get("state") == "detenido" for _, data in events))


if __name__ == "__main__": unittest.main()
