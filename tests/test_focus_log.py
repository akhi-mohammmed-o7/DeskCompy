"""Focus log, streaks, the exclusive streak set, and the sound cues."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import focus_history  # noqa: E402
import rewards  # noqa: E402
import settings_store  # noqa: E402
import sounds  # noqa: E402
from settings_store import Settings, load_settings  # noqa: E402

TODAY = date(2026, 11, 11)


def entries(*days: int, minutes: int = 25) -> list[str]:
    return [f"{(TODAY - timedelta(days=day)).isoformat()}T14:30|{minutes}" for day in days]


class LogTests(unittest.TestCase):
    def test_entries_parse_and_reject_nonsense(self) -> None:
        self.assertEqual(focus_history.parse("2026-11-11T09:05|25")[1:], ("09:05", 25))
        for bad in ("", "nope", "2026-11-11T09:05|", "2026-11-11T09:05|0", "2026-11-11T09:05|9999"):
            self.assertIsNone(focus_history.parse(bad))

    def test_record_appends_and_trims(self) -> None:
        stamp = datetime(2026, 11, 11, 13, 40)
        log = focus_history.record([], 25, now=stamp)
        self.assertEqual(log, ["2026-11-11T13:40|25"])
        log = focus_history.record(log, 5, now=stamp)
        self.assertEqual(log[-1], "2026-11-11T13:40|5")
        long_log = [f"2026-01-01T10:00|25"] * focus_history.MAX_ENTRIES
        self.assertEqual(len(focus_history.record(long_log, 10, now=stamp)), focus_history.MAX_ENTRIES)

    def test_week_groups_by_day_newest_first(self) -> None:
        log = entries(0, 0, 2)
        rows = focus_history.week(log, today=TODAY)
        self.assertEqual(len(rows), 7)
        self.assertEqual(rows[0]["day"], TODAY)
        self.assertEqual(rows[0]["sessions"], 2)
        self.assertEqual(rows[0]["minutes"], 50)
        self.assertEqual(rows[2]["sessions"], 1)
        self.assertEqual(rows[1]["sessions"], 0)
        self.assertEqual(focus_history.week_totals(log, today=TODAY), (3, 75))

    def test_times_are_listed_evening_first(self) -> None:
        log = ["2026-11-11T09:00|25", "2026-11-11T18:00|10"]
        row = focus_history.week(log, today=TODAY)[0]
        self.assertEqual([clock for clock, _minutes in row["times"]], ["18:00", "09:00"])


class StreakTests(unittest.TestCase):
    def test_consecutive_days_count(self) -> None:
        self.assertEqual(focus_history.streak(entries(0, 1, 2), today=TODAY), (3, 3))

    def test_a_gap_starts_a_new_streak(self) -> None:
        self.assertEqual(focus_history.streak(entries(0, 2, 3), today=TODAY), (1, 2))

    def test_yesterday_still_counts_today(self) -> None:
        self.assertEqual(focus_history.streak(entries(1, 2), today=TODAY), (2, 2))

    def test_a_full_missed_day_breaks_it(self) -> None:
        self.assertEqual(focus_history.streak(entries(2, 3), today=TODAY), (0, 2))

    def test_best_can_exceed_current(self) -> None:
        current, best = focus_history.streak(entries(5, 6, 7, 8, 0), today=TODAY)
        self.assertEqual(current, 1)
        self.assertEqual(best, 4)

    def test_broken_entries_are_ignored(self) -> None:
        self.assertEqual(focus_history.streak(["nope"], today=TODAY), (0, 0))


class StreakAccessoryTests(unittest.TestCase):
    def test_exclusive_set_needs_a_streak(self) -> None:
        self.assertFalse(rewards.is_unlocked("circlet", 999, 99, 2))
        self.assertTrue(rewards.is_unlocked("circlet", 0, 0, 3))
        self.assertFalse(rewards.is_unlocked("medal", 999, 99, 6))
        self.assertTrue(rewards.is_unlocked("medal", 0, 0, 7))
        self.assertTrue(rewards.is_unlocked("streak_cape", 0, 0, 14))

    def test_streak_items_are_not_wearable_early(self) -> None:
        self.assertEqual(rewards.owned_accessory("medal", 500, 50, 6), "none")
        self.assertEqual(rewards.owned_accessory("medal", 0, 0, 7), "medal")

    def test_requirement_mentions_the_streak(self) -> None:
        self.assertIn("3-day streak", rewards.BY_KEY["circlet"].requirement())

    def test_streak_items_unlock_when_the_streak_grows(self) -> None:
        before = rewards.unlocked(0, 0, 2)
        after = rewards.unlocked(0, 0, 3)
        gained = [item.key for item in rewards.newly_unlocked(before, after)]
        self.assertEqual(gained, ["circlet"])


class SoundTests(unittest.TestCase):
    def test_every_cue_is_a_valid_wav(self) -> None:
        for name in sounds._KEYS:
            data = sounds.build(name)
            self.assertTrue(data.startswith(b"RIFF"), name)
            self.assertGreater(len(data), 44, name)
            self.assertLess(len(data), 60_000, name)

    def test_unknown_cues_are_rejected(self) -> None:
        with self.assertRaises(KeyError):
            sounds.build("trumpet")
        self.assertFalse(sounds.play("trumpet"))

    def test_tick_is_quieter_and_shorter_than_a_gesture(self) -> None:
        self.assertLess(len(sounds.build("tick")), len(sounds.build("flutter")))


class FocusLogSettingsTests(unittest.TestCase):
    def test_log_roundtrip_and_salvage(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "settings.json"
            original = settings_store.settings_file
            settings_store.settings_file = lambda: target
            try:
                Settings(focus_log=["2026-11-11T14:00|25"]).save()
                self.assertEqual(load_settings().focus_log, ["2026-11-11T14:00|25"])
                target.write_text(
                    json.dumps(
                        {
                            "focus_log": [
                                "2026-11-11T14:00|25",
                                "bad",
                                42,
                                "2026-11-11T15:00|9999",
                            ]
                        }
                    ),
                    encoding="utf-8",
                )
                self.assertEqual(load_settings().focus_log, ["2026-11-11T14:00|25"])
            finally:
                settings_store.settings_file = original


if __name__ == "__main__":
    unittest.main()
