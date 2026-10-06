import json
import tempfile
import unittest
from pathlib import Path
from src.core.persistence import load_settings


class LegacySettingsTests(unittest.TestCase):
    def test_old_invoice_types_are_ignored(self):
        for mode in ("antiguas", "modernas", "automatico"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "config.json"
                path.write_text(json.dumps({"caja": "Hotel", "inicial": 1,
                                            "final": 2, "notice_mode": mode}), encoding="utf-8")
                settings = load_settings(path)
                self.assertEqual(settings["caja"], "Hotel")
                self.assertNotIn("notice_mode", settings)
