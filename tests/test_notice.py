import json
import logging
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from src.core.notice import MODE_LABELS, NoticeCoordinator, NoticeMode
from src.core.persistence import load_settings
from src.core.utils import AutomationStopped, ExecutionControl


class ManualNoticeTests(unittest.TestCase):
    def test_manual_modes_for_both_boxes(self):
        for caja in ("Hotel", "Albergue"):
            for mode in NoticeMode:
                with self.subTest(caja=caja, mode=mode), patch("src.core.notice.press_key") as press:
                    NoticeCoordinator(logging.getLogger("test")).handle(caja, 7, mode, ExecutionControl())
                    if mode is NoticeMode.OLD:
                        self.assertEqual(press.call_count, 1)
                        self.assertEqual(press.call_args.args[0], "enter")
                    else:
                        press.assert_not_called()

    def test_stop_prevents_acceptance(self):
        control = ExecutionControl()
        control.stop_event.set()
        with patch("src.core.notice.press_key") as press:
            with self.assertRaises(AutomationStopped):
                NoticeCoordinator(logging.getLogger("test")).handle("Hotel", 7, NoticeMode.OLD, control)
            press.assert_not_called()

    def test_only_manual_modes_are_available(self):
        self.assertEqual(set(MODE_LABELS), {NoticeMode.OLD, NoticeMode.MODERN})


class LegacyModeTests(unittest.TestCase):
    def test_saved_automatic_mode_becomes_manual(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "config.json"
            path.write_text(json.dumps({"caja": "Hotel", "inicial": 1,
                                        "final": 2, "notice_mode": "automatico"}), encoding="utf-8")
            self.assertEqual(load_settings(path)["notice_mode"], "modernas")
