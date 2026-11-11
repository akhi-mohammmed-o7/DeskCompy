"""The glimmer ledger: day rollover, the seven-day window, and settings."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import glimmer  # noqa: E402
import settings_store  # noqa: E402
from settings_store import Settings, load_settings  # noqa: E402


class GlimmerTests(unittest.TestCase):
    def test_work_is_credited_to_today(self) -> None:
        settings = Settings(glimmer_date="2026-11-10", glimmer_seconds=10)
        glimmer.add_seconds(settings, 5.5, today="2026-11-10")
        self.assertEqual(settings.glimmer_seconds, 15.5)
        self.assertEqual(settings.history, {})

    def test_turning_the_date_archives_the_finished_day(self) -> None:
        settings = Settings(glimmer_date="2026-11-09", glimmer_seconds=600)
        glimmer.add_seconds(settings, 2, today="2026-11-10")
        self.assertEqual(settings.history["2026-11-09"], 600)
        self.assertEqual(settings.glimmer_seconds, 2)
        self.assertEqual(settings.glimmer_date, "2026-11-10")

    def test_zero_seconds_still_rolls_the_date(self) -> None:
        settings = Settings(glimmer_date="2026-11-09", glimmer_seconds=90)
        glimmer.add_seconds(settings, 0, today="2026-11-10")
        self.assertEqual(settings.history["2026-11-09"], 90)
        self.assertEqual(settings.glimmer_seconds, 0)

    def test_the_week_is_seven_days_oldest_first(self) -> None:
        settings = Settings(glimmer_date="2026-11-10", glimmer_seconds=120)
        settings.history = {"2026-11-04": 60, "2026-11-08": 300}
        series = glimmer.week(settings, today="2026-11-10")
        self.assertEqual(len(series), 7)
        self.assertEqual(series[0][0], "2026-11-04")
        self.assertEqual(series[-1][0], "2026-11-10")
        self.assertTrue(series[-1][2])
        self.assertEqual(series[-1][1], 120)
        self.assertEqual(series[4][1], 300)
        self.assertEqual(glimmer.week_minutes(settings, today="2026-11-10"), 8)

    def test_an_old_today_credit_is_not_reused(self) -> None:
        settings = Settings(glimmer_date="2026-11-08", glimmer_seconds=999)
        series = glimmer.week(settings, today="2026-11-10")
        self.assertEqual(series[-1][1], 0)

    def test_history_is_trimmed(self) -> None:
        settings = Settings()
        settings.history = {f"2026-01-{day:02d}": 60 for day in range(1, 20)}
        glimmer.add_seconds(settings, 1, today="2026-02-01")
        self.assertLessEqual(len(settings.history), glimmer.MAX_HISTORY)
        self.assertTrue(all(key >= "2026-01-22" for key in settings.history))
        self.assertNotIn("2026-01-01", settings.history)


class SettingsFieldTests(unittest.TestCase):
    def test_history_and_dim_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "settings.json"
            original = settings_store.settings_file
            settings_store.settings_file = lambda: target
            try:
                Settings(dim_focus=False, history={"2026-11-09": 42.5}).save()
                loaded = load_settings()
                self.assertFalse(loaded.dim_focus)
                self.assertEqual(loaded.history, {"2026-11-09": 42.5})

                target.write_text(
                    json.dumps(
                        {
                            "dim_focus": "yes",
                            "history": {
                                "2026-11-09": 30,
                                "2026-11-10": -5,
                                "bad": 10,
                                "toolong-key": 10,
                                "2026-11-08": True,
                            },
                        }
                    ),
                    encoding="utf-8",
                )
                salvaged = load_settings()
                self.assertTrue(salvaged.dim_focus)
                self.assertEqual(salvaged.history, {"2026-11-09": 30.0})
            finally:
                settings_store.settings_file = original


if __name__ == "__main__":
    unittest.main()
