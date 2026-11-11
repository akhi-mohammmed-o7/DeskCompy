"""Rewards, coats, and the focus-timer ledger."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import rewards  # noqa: E402
import settings_store  # noqa: E402
import theme  # noqa: E402
from settings_store import Settings, load_settings  # noqa: E402


class AccessoryTests(unittest.TestCase):
    def test_catalog_is_unique_and_mostly_earned(self) -> None:
        keys = [item.key for item in rewards.ACCESSORIES]
        self.assertEqual(len(keys), len(set(keys)))
        free = [item for item in rewards.ACCESSORIES if item.free]
        self.assertGreaterEqual(len(free), 2)
        self.assertGreater(len(rewards.ACCESSORIES) - len(free), len(free) * 4)
        self.assertEqual(rewards.BY_KEY["none"].style, "none")

    def test_nothing_is_earned_at_zero_except_the_starters(self) -> None:
        earned = rewards.unlocked(0, 0)
        self.assertTrue(all(item.free for item in earned))
        self.assertFalse(rewards.is_unlocked("beanie", 14.9, 0))
        self.assertTrue(rewards.is_unlocked("beanie", 15, 0))

    def test_sessions_and_minutes_both_unlock(self) -> None:
        self.assertFalse(rewards.is_unlocked("party_hat", 0, 0))
        self.assertTrue(rewards.is_unlocked("party_hat", 0, 1))
        self.assertFalse(rewards.is_unlocked("headphones", 29, 99))
        self.assertTrue(rewards.is_unlocked("headphones", 30, 0))

    def test_new_unlocks_are_the_difference(self) -> None:
        before = rewards.unlocked(0, 0)
        after = rewards.unlocked(0, 1)
        gained = rewards.newly_unlocked(before, after)
        self.assertEqual([item.key for item in gained], ["party_hat"])
        self.assertEqual(rewards.newly_unlocked(after, after), [])

    def test_next_locked_names_a_real_target(self) -> None:
        nxt = rewards.next_locked(0, 0)
        self.assertIsNotNone(nxt)
        self.assertFalse(nxt.free)
        self.assertFalse(rewards.is_unlocked(nxt.key, 0, 0))

    def test_only_earned_accessories_can_be_worn(self) -> None:
        self.assertEqual(rewards.owned_accessory("crown", 0, 0), "none")
        self.assertEqual(rewards.owned_accessory("glasses", 0, 0), "glasses")
        self.assertEqual(rewards.owned_accessory("crown", 200, 0), "crown")
        self.assertEqual(rewards.owned_accessory("not-real", 900, 90), "none")

    def test_requirements_read_well(self) -> None:
        self.assertIn("focus minutes", rewards.BY_KEY["beanie"].requirement())
        self.assertIn("session", rewards.BY_KEY["party_hat"].requirement())


class CoatTests(unittest.TestCase):
    def test_natural_leaves_colours_alone(self) -> None:
        buddy = __import__("characters").CHARACTERS["cat"]
        self.assertIs(theme.recolour(buddy, theme.NATURAL), buddy)
        self.assertEqual(theme.tint_rgb((10, 20, 30), theme.NATURAL), (10, 20, 30))

    def test_coats_tint_without_replacing_the_buddy(self) -> None:
        buddy = __import__("characters").CHARACTERS["cat"]
        coated = theme.recolour(buddy, "mint")
        self.assertNotEqual(coated.body, buddy.body)
        self.assertEqual(coated.key, buddy.key)
        self.assertEqual(coated.trim, theme.mix(buddy.trim, theme.coat_look("mint")[0], 0.42 * 0.28))

    def test_every_coat_has_a_label_and_a_tint(self) -> None:
        for coat in theme.COAT_ORDER:
            self.assertIn(coat, theme.COAT_LABELS)
            if coat == theme.NATURAL:
                self.assertIsNone(theme.coat_look(coat))
            else:
                self.assertIsNotNone(theme.coat_look(coat))

    def test_palettes_are_all_complete(self) -> None:
        for name in theme.PALETTE_ORDER:
            self.assertEqual(len(theme.PALETTES[name]), 9)
        self.assertGreaterEqual(len(theme.PALETTE_ORDER), 8)


class FocusLedgerTests(unittest.TestCase):
    def test_focus_fields_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "settings.json"
            original = settings_store.settings_file
            settings_store.settings_file = lambda: target
            try:
                Settings(
                    coat="mint",
                    accessory="beanie",
                    focus_minutes=40,
                    focus_sessions=4,
                    focus_minutes_total=95.5,
                ).save()
                loaded = load_settings()
                self.assertEqual(loaded.coat, "mint")
                self.assertEqual(loaded.accessory, "beanie")
                self.assertEqual(loaded.focus_minutes, 40)
                self.assertEqual(loaded.focus_sessions, 4)
                self.assertEqual(loaded.focus_minutes_total, 95.5)
            finally:
                settings_store.settings_file = original

    def test_bad_focus_values_are_clamped_or_dropped(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "settings.json"
            original = settings_store.settings_file
            settings_store.settings_file = lambda: target
            try:
                target.write_text(
                    json.dumps(
                        {
                            "coat": "plaid",
                            "accessory": "rocket",
                            "focus_minutes": 300,
                            "focus_sessions": -4,
                            "focus_minutes_total": -2,
                        }
                    ),
                    encoding="utf-8",
                )
                loaded = load_settings()
                self.assertEqual(loaded.coat, "natural")
                self.assertEqual(loaded.accessory, "glasses")
                self.assertEqual(loaded.focus_minutes, 60)
                self.assertEqual(loaded.focus_sessions, 0)
                self.assertEqual(loaded.focus_minutes_total, 0.0)
            finally:
                settings_store.settings_file = original

    def test_legacy_veil_becomes_the_dim_preference(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "settings.json"
            original = settings_store.settings_file
            settings_store.settings_file = lambda: target
            try:
                target.write_text(json.dumps({"veil": True}), encoding="utf-8")
                self.assertTrue(load_settings().dim_focus)
                target.write_text(json.dumps({"dim_focus": False}), encoding="utf-8")
                self.assertFalse(load_settings().dim_focus)
            finally:
                settings_store.settings_file = original


if __name__ == "__main__":
    unittest.main()
