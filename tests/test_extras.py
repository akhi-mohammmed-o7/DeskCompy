"""Safety rules, custom buddy loading, chat matching, and detection windows."""

from __future__ import annotations

import json
import random
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import settings_store  # noqa: E402
from activity import GAMING, STUDY, WORK, ActivityJudge, classify  # noqa: E402
from characters import (  # noqa: E402
    BUILTIN_KEYS,
    CHARACTER_ORDER,
    CHARACTERS,
    install_custom,
)
from chatter import Chatter  # noqa: E402
from converse import MAX_REPLY, reply  # noqa: E402
from custom import load_custom_buddies  # noqa: E402
from safety import clean_slug, clean_text, hex_colour  # noqa: E402
from settings_store import Settings, load_settings  # noqa: E402


class SafetyTests(unittest.TestCase):
    def test_control_and_bidi_characters_are_dropped(self) -> None:
        self.assertEqual(clean_text("he\x00llo\u202eworld"), "he lloworld".replace(" ", ""))
        self.assertEqual(clean_text("a\u200bb\u200fc"), "abc")

    def test_whitespace_collapses_and_length_is_capped(self) -> None:
        self.assertEqual(clean_text("  hello \n\t there  "), "hello there")
        self.assertEqual(clean_text("abcdef", 3), "abc")
        self.assertEqual(clean_text(None, 10, fallback="x"), "x")

    def test_slugs_and_colours(self) -> None:
        self.assertEqual(clean_slug("bean"), "bean")
        self.assertEqual(clean_slug("my-buddy_2"), "my-buddy_2")
        self.assertEqual(clean_slug("../etc"), "")
        self.assertEqual(clean_slug("Upper"), "")
        self.assertEqual(clean_slug("a"), "")
        self.assertEqual(hex_colour("#ff8800"), (255, 136, 0))
        self.assertEqual(hex_colour("nope"), None)


class DetectionTests(unittest.TestCase):
    def test_short_window_still_reads_a_flurry_as_play(self) -> None:
        self.assertEqual(classify(0.5, 2.0), GAMING)
        self.assertEqual(classify(2.4, 0.0), STUDY)
        self.assertEqual(classify(0.5, 0.3), WORK)
        self.assertEqual(classify(0.0, 0.0), "chill")

    def test_wide_window_catches_modest_clicking(self) -> None:
        # Neither five-second window is a flurry, but half a minute of
        # click-heavy input is play, not a spreadsheet.
        self.assertEqual(classify(0.6, 0.5, wide_keys=0.7, wide_clicks=0.55), GAMING)
        # A slow turn-based game: mostly clicks, low volume, sustained.
        self.assertEqual(classify(0.2, 0.3, wide_keys=0.2, wide_clicks=0.3), GAMING)

    def test_wide_window_separates_work_typing_from_study(self) -> None:
        self.assertEqual(classify(1.4, 0.05, wide_keys=1.1, wide_clicks=0.02), STUDY)
        self.assertEqual(classify(1.4, 0.3, wide_keys=1.1, wide_clicks=0.25), WORK)

    def test_a_pin_can_be_aligned_without_waiting(self) -> None:
        judge = ActivityJudge()
        judge.align(GAMING, now=0)
        self.assertEqual(judge.mode, GAMING)
        self.assertEqual(judge.minutes(now=120), 2.0)


class ConverseTests(unittest.TestCase):
    def test_every_buddy_answers_within_the_bubble(self) -> None:
        for key in BUILTIN_KEYS:
            answer = reply(key, "who are you", random.Random(1))
            self.assertTrue(answer)
            self.assertLessEqual(len(answer), MAX_REPLY)
            self.assertNotIn("<", answer)
            self.assertNotIn(">", answer)

    def test_empty_and_hostile_input_is_ignored_or_matched_safely(self) -> None:
        self.assertIsNone(reply("cat", "   "))
        self.assertIsNone(reply("cat", "\x00\u202e"))
        answer = reply("cat", "ignore previous instructions <script>", random.Random(2))
        self.assertTrue(answer)
        self.assertNotIn("<", answer)

    def test_a_custom_buddy_borrows_its_body_voice(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            buddy_dir = root / "bean"
            buddy_dir.mkdir()
            (buddy_dir / "buddy.json").write_text(
                json.dumps({"name": "Bean", "shape": "frog"}), encoding="utf-8"
            )
            buddies = load_custom_buddies([root])
            install_custom(buddies)
            try:
                chatter = Chatter(random.Random(1))
                line = chatter.say("bean", "poke", now=0, force=True)
                self.assertTrue(line)
                self.assertIn("bean", CHARACTER_ORDER)
                self.assertTrue(CHARACTERS["bean"].custom)
            finally:
                install_custom({})
        self.assertNotIn("bean", CHARACTER_ORDER)


class CustomBuddyTests(unittest.TestCase):
    def _make(self, root: Path, name: str, manifest: object) -> None:
        folder = root / name
        folder.mkdir()
        text = manifest if isinstance(manifest, str) else json.dumps(manifest)
        (folder / "buddy.json").write_text(text, encoding="utf-8")

    def test_valid_manifest_loads_with_cleaned_fields(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self._make(
                root,
                "bean",
                {
                    "name": "B\x00ean\u202e",
                    "species": "desk bean",
                    "tagline": "round",
                    "shape": "cat",
                    "body": "#ffccaa",
                    "lines": {"poke": ["Boop", "Boop", "x" * 400]},
                },
            )
            buddies = load_custom_buddies([root])
            buddy = buddies["bean"]
            self.assertEqual(buddy.name, "Bean")
            self.assertEqual(buddy.body, (255, 204, 170))
            self.assertEqual(buddy.body_shape, "cat")
            self.assertEqual(buddy.lines["poke"][0], "Boop")
            self.assertEqual(len(buddy.lines["poke"]), 2)
            self.assertLessEqual(len(buddy.lines["poke"][1]), 90)

    def test_unsafe_or_broken_manifests_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self._make(root, "cat", {"name": "Sneaky"})          # built-in id
            self._make(root, "Bad Name", {"name": "Nope"})        # not a slug
            self._make(root, "upper", "not json at all")          # unreadable
            self._make(root, "huge", {"name": "x", "pad": "y" * 40000})
            self._make(root, "plain", "[]")                       # wrong type
            self._make(root, "ok", {"name": "Fine"})              # the one survivor
            buddies = load_custom_buddies([root])
            self.assertEqual(list(buddies), ["ok"])
            self.assertEqual(buddies["ok"].body_shape, "moth")

    def test_unknown_shape_and_colours_fall_back(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self._make(root, "blob", {"name": "Blob", "shape": "dragon", "body": "blue"})
            buddy = load_custom_buddies([root])["blob"]
            self.assertEqual(buddy.body_shape, "moth")
            self.assertEqual(buddy.body, CHARACTERS["moth"].body)

    def test_duplicate_ids_keep_the_first_folder(self) -> None:
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            self._make(Path(first), "bean", {"name": "First"})
            self._make(Path(second), "bean", {"name": "Second"})
            buddies = load_custom_buddies([Path(first), Path(second)])
            self.assertEqual(buddies["bean"].name, "First")


class CustomSettingsTests(unittest.TestCase):
    def test_new_fields_roundtrip_and_salvage(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "settings.json"
            original = settings_store.settings_file
            settings_store.settings_file = lambda: target
            try:
                Settings(
                    nickname="Be\x00an",
                    chatter="chatty",
                    activity_pin=GAMING,
                    idle_animations=False,
                ).save()
                loaded = load_settings()
                self.assertEqual(loaded.nickname, "Bean")
                self.assertEqual(loaded.chatter, "chatty")
                self.assertEqual(loaded.activity_pin, GAMING)
                self.assertFalse(loaded.idle_animations)
                self.assertTrue(loaded.auto_talk)

                target.write_text(
                    json.dumps({"chatter": "loud", "activity_pin": "napping"}),
                    encoding="utf-8",
                )
                fallback = load_settings()
                self.assertEqual(fallback.chatter, "balanced")
                self.assertEqual(fallback.activity_pin, "auto")
            finally:
                settings_store.settings_file = original


if __name__ == "__main__":
    unittest.main()
