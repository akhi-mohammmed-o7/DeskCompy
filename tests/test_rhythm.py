"""Rhythm rules and settings, without opening a window or a global hook."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from settings_store import Settings, load_settings  # noqa: E402
import settings_store  # noqa: E402
from states import CALM, SCATTER, SLEEPING, WORKING  # noqa: E402
from tracker import classify  # noqa: E402


class ClassifyTests(unittest.TestCase):
    def test_five_minutes_is_sleep(self) -> None:
        self.assertEqual(classify(0, 0, 300, CALM), SLEEPING)
        self.assertEqual(classify(0, 0, 299, CALM), CALM)

    def test_typing_is_working_and_clicks_are_scatter(self) -> None:
        self.assertEqual(classify(8, 0, 0.2, CALM), WORKING)
        self.assertEqual(classify(0, 4, 0.2, CALM), SCATTER)

    def test_the_busier_hand_wins_when_both_are_busy(self) -> None:
        self.assertEqual(classify(8, 9, 0.2, CALM), SCATTER)
        self.assertEqual(classify(9, 4, 0.2, CALM), WORKING)

    def test_a_short_pause_does_not_drop_glimmer(self) -> None:
        self.assertEqual(classify(0, 0, 5, WORKING), WORKING)
        self.assertEqual(classify(0, 0, 6, WORKING), CALM)

    def test_sleep_wins_over_a_held_state(self) -> None:
        self.assertEqual(classify(0, 0, 300, WORKING), SLEEPING)


class SettingsTests(unittest.TestCase):
    def test_roundtrip_and_rejects_unknown_palette(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "settings.json"
            original = settings_store.settings_file
            settings_store.settings_file = lambda: target
            try:
                Settings(x=12, intention="hold the line", palette="tide", glimmer_seconds=90).save()
                loaded = load_settings()
                self.assertEqual(loaded.x, 12)
                self.assertEqual(loaded.intention, "hold the line")
                self.assertEqual(loaded.palette, "tide")
                self.assertEqual(loaded.glimmer_seconds, 90)

                target.write_text(json.dumps({"palette": "nope", "x": 3}), encoding="utf-8")
                fallback = load_settings()
                self.assertEqual(fallback.palette, "amber")
                self.assertEqual(fallback.x, 3)

                target.write_text("{not json", encoding="utf-8")
                self.assertEqual(load_settings().x, None)
            finally:
                settings_store.settings_file = original


if __name__ == "__main__":
    unittest.main()
