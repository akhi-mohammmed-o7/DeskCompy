"""Buddy behavior: activity inference, voices, mirroring, and saved choice."""

from __future__ import annotations

import json
import random
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import settings_store  # noqa: E402
from activity import (  # noqa: E402
    AWAY,
    CHILL,
    GAMING,
    STUDY,
    WORK,
    ActivityJudge,
    classify,
    typing_continuity,
)
from characters import CHARACTER_ORDER, CHARACTERS, get, next_key  # noqa: E402
from chatter import COOLDOWN, LINES, SITUATIONS, Chatter  # noqa: E402
from reactions import MAX_KEYCAPS, MAX_RIPPLES, Mirror  # noqa: E402
from tricks import tricks_for  # noqa: E402
from settings_store import Settings, load_settings  # noqa: E402


class ActivityTests(unittest.TestCase):
    def test_rates_map_to_activities(self) -> None:
        # Fast typing is work; steady note-paced typing is study.
        self.assertEqual(classify(2.4, 0.0), WORK)
        self.assertEqual(classify(1.2, 0.0, continuity=0.9), STUDY)
        self.assertEqual(classify(1.2, 0.4, continuity=0.9), WORK)
        self.assertEqual(classify(0.5, 2.0), GAMING)
        self.assertEqual(classify(0.5, 0.3), WORK)
        self.assertEqual(classify(0.2, 0.2), WORK)
        self.assertEqual(classify(0.0, 0.0), CHILL)

    def test_a_shy_typing_rate_is_not_studying(self) -> None:
        # A single tap, or intermittent keys with no continuity, is just work.
        self.assertEqual(classify(0.6, 0.0, continuity=0.1), WORK)
        self.assertEqual(classify(0.05, 0.0), CHILL)

    def test_slow_clicking_is_work_not_gaming(self) -> None:
        self.assertEqual(classify(0.0, 0.4), WORK)
        self.assertEqual(classify(0.0, 1.7), GAMING)
        # Sustained clicking with almost no typing also reads as play.
        self.assertEqual(
            classify(0.2, 0.8, wide_keys=0.1, wide_clicks=0.8), GAMING
        )

    def test_a_short_pause_keeps_the_desk_busy(self) -> None:
        judge = ActivityJudge()
        self.assertEqual(judge.observe(3, 0, 0.1, now=0), WORK)
        self.assertEqual(judge.observe(0, 0, 3.0, now=1), WORK)
        self.assertEqual(judge.observe(0, 0, 6.0, now=2), WORK)
        self.assertEqual(judge.observe(0, 0, 23.0, now=3), CHILL)

    def test_gaming_lingers_briefly_then_clears(self) -> None:
        judge = ActivityJudge()
        judge.observe(0, 2, 0.1, now=0)
        judge.observe(0, 2, 0.1, now=1)
        self.assertEqual(judge.mode, GAMING)
        self.assertEqual(judge.observe(0, 0, 4.0, now=2), GAMING)
        self.assertEqual(judge.observe(0, 0, 9.0, now=3), CHILL)

    def test_continuity_needs_real_history(self) -> None:
        self.assertIsNone(typing_continuity([(3, 0), (2, 0)]))
        busy = [(2, 0)] * 10 + [(0, 1)] * 10
        self.assertAlmostEqual(typing_continuity(busy), 0.5)
        steady = [(1, 0)] * 20
        self.assertAlmostEqual(typing_continuity(steady), 1.0)

    def test_five_quiet_minutes_is_away(self) -> None:
        judge = ActivityJudge()
        self.assertEqual(judge.observe(0, 0, 10, now=0), CHILL)
        self.assertEqual(judge.observe(0, 0, 299, now=1), CHILL)
        self.assertEqual(judge.observe(0, 0, 300, now=2), AWAY)

    def test_a_single_burst_does_not_change_the_mood(self) -> None:
        judge = ActivityJudge()
        self.assertEqual(judge.observe(0, 0, 1, now=0), CHILL)
        self.assertEqual(judge.observe(0, 2.0, 0.1, now=1), CHILL)
        self.assertEqual(judge.observe(0, 0.0, 0.1, now=2), CHILL)
        self.assertEqual(judge.observe(0, 2.0, 0.1, now=3), CHILL)
        self.assertEqual(judge.observe(0, 2.0, 0.1, now=4), GAMING)

    def test_the_clock_restarts_when_the_activity_changes(self) -> None:
        judge = ActivityJudge()
        judge.observe(3, 0, 0.1, now=100)
        judge.observe(3, 0, 0.1, now=400)
        self.assertEqual(judge.minutes(now=400), 5.0)
        judge.observe(0, 2, 0.1, now=500)
        judge.observe(0, 2, 0.1, now=560)
        self.assertEqual(judge.mode, GAMING)
        self.assertAlmostEqual(judge.minutes(now=620), 1.0, places=3)


class RosterTests(unittest.TestCase):
    def test_eight_distinct_buddies_and_a_wrapping_next(self) -> None:
        self.assertEqual(len(CHARACTER_ORDER), 8)
        self.assertEqual(len(set(CHARACTER_ORDER)), 8)
        for key in CHARACTER_ORDER:
            self.assertIn(key, CHARACTERS)
            self.assertTrue(CHARACTERS[key].name)
            self.assertTrue(CHARACTERS[key].tagline)
        self.assertEqual(next_key(CHARACTER_ORDER[-1]), CHARACTER_ORDER[0])
        self.assertEqual(get("nope").key, "moth")

    def test_every_buddy_has_a_voice_for_every_situation(self) -> None:
        for key in CHARACTER_ORDER:
            self.assertIn(key, LINES)
            for situation in SITUATIONS:
                self.assertIn(situation, LINES[key], f"{key} is silent on {situation}")
                self.assertIn(situation, COOLDOWN)
                self.assertTrue(LINES[key][situation])

    def test_every_body_has_its_own_performances(self) -> None:
        for key in CHARACTER_ORDER:
            pool = tricks_for(CHARACTERS[key].body_shape)
            self.assertTrue(pool, f"{key} has no tricks")
            self.assertTrue(all(trick.key for trick in pool))
            # Each body keeps at least one gesture of its own, not just travel.
            self.assertTrue(any(trick.gesture for trick in pool), key)
        self.assertTrue(tricks_for("dragon"))


class ChatterTests(unittest.TestCase):
    def test_it_respects_the_global_gap(self) -> None:
        chatter = Chatter(random.Random(1), min_gap=9.0)
        self.assertIsNotNone(chatter.say("cat", "meet", now=100))
        self.assertIsNone(chatter.say("cat", "poke", now=101))
        self.assertIsNotNone(chatter.say("cat", "poke", now=110))
        self.assertIsNotNone(chatter.say("cat", "poke", now=114, force=True))

    def test_it_does_not_repeat_the_same_line_twice(self) -> None:
        chatter = Chatter(random.Random(3))
        first = chatter.say("ghost", "meet", now=0, force=True)
        second = chatter.say("ghost", "meet", now=1, force=True)
        self.assertNotEqual(first, second)

    def test_an_unknown_buddy_still_says_something(self) -> None:
        chatter = Chatter(random.Random(2))
        self.assertIsNotNone(chatter.say("dragon", "poke", now=0, force=True))


class MirrorTests(unittest.TestCase):
    def test_keycaps_are_capped_and_expire(self) -> None:
        mirror = Mirror(random.Random(4))
        for _ in range(30):
            mirror.typed(3)
        self.assertLessEqual(len(mirror._caps), MAX_KEYCAPS)
        self.assertGreater(mirror.typing, 0.0)
        for _ in range(200):
            mirror.advance(0.05)
        self.assertFalse(mirror.busy)
        self.assertEqual(mirror.typing, 0.0)

    def test_clicks_are_capped_and_raise_the_squash(self) -> None:
        mirror = Mirror(random.Random(5))
        for _ in range(10):
            mirror.clicked()
        self.assertLessEqual(len(mirror._ripples), MAX_RIPPLES)
        self.assertGreater(mirror.clicking, 0.5)
        for _ in range(40):
            mirror.advance(0.05)
        self.assertLess(mirror.clicking, 0.05)
        mirror.clear()
        self.assertEqual(mirror.clicking, 0.0)


class CharacterSettingTests(unittest.TestCase):
    def test_character_roundtrip_and_salvage(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "settings.json"
            original = settings_store.settings_file
            settings_store.settings_file = lambda: target
            try:
                Settings(character="axolotl").save()
                self.assertEqual(load_settings().character, "axolotl")
                target.write_text(json.dumps({"character": "dragon"}), encoding="utf-8")
                self.assertEqual(load_settings().character, "moth")
                target.write_text(json.dumps({"character": 7}), encoding="utf-8")
                self.assertEqual(load_settings().character, "moth")
            finally:
                settings_store.settings_file = original


if __name__ == "__main__":
    unittest.main()
