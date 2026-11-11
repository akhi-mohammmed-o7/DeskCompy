"""Accessories earned by keeping focus sessions.

A session is a completed focus timer. Only finished sessions count: cancelling
one earns nothing. Every accessory except the starter pair is locked behind a
number of completed sessions or a total of focused minutes, and the wardrobe
shows the requirement instead of hiding what is still out there.

Pure data and arithmetic, so the rules are testable without Qt.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Accessory:
    key: str
    label: str
    # How it sits on the body: hat / face / neck / back / above.
    style: str
    sessions: int = 0
    minutes: int = 0
    streak: int = 0
    hint: str = ""

    @property
    def free(self) -> bool:
        return self.sessions <= 0 and self.minutes <= 0 and self.streak <= 0

    def requirement(self) -> str:
        if self.free:
            return "Always available"
        parts: list[str] = []
        if self.minutes:
            parts.append(f"{self.minutes} focus minutes")
        if self.streak:
            parts.append(f"a {self.streak}-day streak")
        if self.sessions:
            parts.append(f"{self.sessions} completed session{'s' if self.sessions != 1 else ''}")
        return " · ".join(parts)


NONE = Accessory("none", "No accessory", "none")

ACCESSORIES: tuple[Accessory, ...] = (
    NONE,
    Accessory("glasses", "Reading glasses", "face", hint="A studious look, free from day one."),
    Accessory("bow_tie", "Little bow tie", "neck", hint="Small, formal, extremely serious."),
    Accessory("beanie", "Cozy beanie", "hat", minutes=15, hint="Warm ears after a quarter hour."),
    Accessory("party_hat", "Party hat", "hat", sessions=1, hint="One finished focus earns confetti."),
    Accessory("headphones", "Study headphones", "neck", minutes=30, hint="For the deep-work stretch."),
    Accessory("top_hat", "Tiny top hat", "hat", minutes=60, hint="An hour of focus, formally dressed."),
    Accessory("scarf", "Long scarf", "neck", sessions=3, hint="Three finished sessions."),
    Accessory("crown", "Paper crown", "hat", minutes=120, hint="Two hours of kept focus."),
    Accessory("monocle", "Monocle", "face", sessions=5, hint="Five sessions of scrutiny."),
    Accessory("sunglasses", "Tiny sunglasses", "face", sessions=8, hint="Cool, but only after eight sessions."),
    Accessory("flower", "Ear flower", "hat", sessions=12, hint="Twelve sessions and blooming."),
    Accessory("wizard_hat", "Wizard hat", "hat", minutes=240, hint="Four hours of focus: magic."),
    Accessory("halo", "Little halo", "above", minutes=360, hint="Six hours of focus, and glowing."),
    Accessory("propeller", "Propeller cap", "hat", sessions=20, hint="Twenty sessions, airborne."),
    Accessory("cape", "Hero cape", "back", minutes=600, hint="Ten hours kept: hero material."),
    Accessory("crown_jewel", "Jeweled crown", "hat", sessions=40, hint="Forty sessions. The long haul."),
    # Exclusive streak set: only consecutive days earn these.
    Accessory("circlet", "Ember circlet", "hat", streak=3, hint="Three days in a row."),
    Accessory("medal", "Streak medal", "neck", streak=7, hint="A full week without a gap."),
    Accessory("streak_cape", "Constellation cape", "back", streak=14, hint="Fourteen days. The sky itself."),
)

ACCESSORY_KEYS = tuple(item.key for item in ACCESSORIES)
BY_KEY = {item.key: item for item in ACCESSORIES}
DEFAULT_ACCESSORY = "glasses"


def unlocked(minutes: float, sessions: int, streak: int = 0) -> tuple[Accessory, ...]:
    """Everything earned with this much time, sessions, and current streak."""
    earned = []
    for item in ACCESSORIES:
        if item.free:
            earned.append(item)
        elif (
            (not item.minutes or minutes >= item.minutes)
            and (not item.sessions or sessions >= item.sessions)
            and (not item.streak or streak >= item.streak)
        ):
            earned.append(item)
    return tuple(earned)


def is_unlocked(key: str, minutes: float, sessions: int, streak: int = 0) -> bool:
    return any(item.key == key for item in unlocked(minutes, sessions, streak))


def newly_unlocked(before: tuple[Accessory, ...], after: tuple[Accessory, ...]) -> list[Accessory]:
    seen = {item.key for item in before}
    return [item for item in after if item.key not in seen]


def next_locked(minutes: float, sessions: int, streak: int = 0) -> Accessory | None:
    """The nearest accessory still out of reach, for the wardrobe header."""
    best: Accessory | None = None
    best_score = float("inf")
    have = {item.key for item in unlocked(minutes, sessions, streak)}
    for item in ACCESSORIES:
        if item.key in have:
            continue
        if item.streak:
            score = max(0.0, item.streak - streak) / max(1, item.streak)
        elif item.minutes:
            score = max(0.0, item.minutes - minutes) / max(1, item.minutes)
        else:
            score = max(0.0, item.sessions - sessions) / max(1, item.sessions)
        if score < best_score:
            best_score = score
            best = item
    return best


def owned_accessory(key: str, minutes: float, sessions: int, streak: int = 0) -> str:
    """A safe accessory id: the equipped one if earned, else no accessory."""
    if key in BY_KEY and is_unlocked(key, minutes, sessions, streak):
        return key
    return NONE.key
