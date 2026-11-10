"""The buddy roster: five small characters with their own shapes and voices.

Everything here is plain data so settings can validate a saved choice without
importing Qt. The drawing lives in :mod:`painter`, and the spoken lines live in
:mod:`chatter`, keyed by the same ids.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Character:
    key: str
    name: str
    species: str
    tagline: str
    # Drawing colours. The moth still borrows the active glass palette instead,
    # so its lantern keeps changing colour; the rest keep their own coats.
    body: tuple[int, int, int]
    trim: tuple[int, int, int]
    accent: tuple[int, int, int]
    # Body to borrow when no image is supplied. Built-ins use their own key.
    shape: str = ""
    # Optional extra lines, keyed by chatter situation. Custom buddies only.
    lines: dict[str, tuple[str, ...]] = field(default_factory=dict)
    custom: bool = False

    @property
    def body_shape(self) -> str:
        return self.shape or self.key


CHARACTERS: dict[str, Character] = {
    "moth": Character(
        key="moth",
        name="Lumen",
        species="lantern moth",
        tagline="keeps the light on",
        body=(58, 36, 78),
        trim=(255, 214, 160),
        accent=(255, 186, 122),
    ),
    "cat": Character(
        key="cat",
        name="Mochi",
        species="loaf cat",
        tagline="quality assurance nap",
        body=(250, 219, 186),
        trim=(84, 58, 62),
        accent=(255, 166, 140),
    ),
    "frog": Character(
        key="frog",
        name="Pip",
        species="pocket frog",
        tagline="ribbit with intent",
        body=(142, 216, 156),
        trim=(42, 92, 64),
        accent=(255, 240, 168),
    ),
    "ghost": Character(
        key="ghost",
        name="Wisp",
        species="desk ghost",
        tagline="haunts your deadlines",
        body=(220, 212, 255),
        trim=(92, 80, 140),
        accent=(196, 178, 255),
    ),
    "axolotl": Character(
        key="axolotl",
        name="Nori",
        species="pocket axolotl",
        tagline="permanently unbothered",
        body=(255, 184, 204),
        trim=(150, 78, 110),
        accent=(255, 232, 240),
    ),
}

BUILTIN_KEYS = ("moth", "cat", "frog", "ghost", "axolotl")
CHARACTER_ORDER: list[str] = list(BUILTIN_KEYS)
DEFAULT_CHARACTER = BUILTIN_KEYS[0]
_CUSTOM_KEYS: set[str] = set()


def get(key: str | None) -> Character:
    """The named character, or Lumen when the key is unknown."""
    if key in CHARACTERS:
        return CHARACTERS[key]
    return CHARACTERS[DEFAULT_CHARACTER]


def next_key(key: str) -> str:
    """The next character in the roster, wrapping around."""
    if not CHARACTER_ORDER:
        return DEFAULT_CHARACTER
    try:
        index = CHARACTER_ORDER.index(key)
    except ValueError:
        index = -1
    return CHARACTER_ORDER[(index + 1) % len(CHARACTER_ORDER)]


def install_custom(buddies: dict[str, Character]) -> None:
    """Replace the custom part of the roster with validated buddies.

    Built-ins can never be replaced, and a custom key that collides with one is
    dropped by the loader before it gets here.
    """
    for key in _CUSTOM_KEYS:
        CHARACTERS.pop(key, None)
    _CUSTOM_KEYS.clear()
    del CHARACTER_ORDER[len(BUILTIN_KEYS) :]
    for key, buddy in buddies.items():
        if key in CHARACTERS or not buddy.custom:
            continue
        CHARACTERS[key] = buddy
        CHARACTER_ORDER.append(key)
        _CUSTOM_KEYS.add(key)
