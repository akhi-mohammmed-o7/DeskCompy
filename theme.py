"""Glass palettes and buddy coat colours. No Qt imports, so settings can
validate names cheaply.
"""

from __future__ import annotations

from dataclasses import replace

AMBER = "amber"
TIDE = "tide"
INK = "ink"
MOSS = "moss"
ROSE = "rose"
DUSK = "dusk"
FROST = "frost"
EMBER = "ember"

PALETTE_ORDER = (AMBER, TIDE, INK, MOSS, ROSE, DUSK, FROST, EMBER)

PALETTE_LABELS = {
    AMBER: "Amber lantern",
    TIDE: "Tide glass",
    INK: "Ink glass",
    MOSS: "Moss glass",
    ROSE: "Rose glass",
    DUSK: "Dusk glass",
    FROST: "Frost glass",
    EMBER: "Ember glass",
}

# wing / vein / body / lantern core / lantern edge / ring / text, RGB
PALETTES: dict[str, dict[str, tuple[int, int, int]]] = {
    AMBER: {
        "wing": (255, 186, 122),
        "wing_calm": (186, 156, 255),
        "vein": (255, 244, 220),
        "body": (54, 32, 72),
        "core": (255, 236, 200),
        "edge": (255, 150, 64),
        "ring": (255, 214, 150),
        "text": (255, 246, 234),
        "plate": (24, 14, 36),
    },
    TIDE: {
        "wing": (130, 214, 204),
        "wing_calm": (126, 168, 230),
        "vein": (226, 255, 248),
        "body": (16, 52, 62),
        "core": (214, 255, 246),
        "edge": (64, 186, 176),
        "ring": (170, 240, 228),
        "text": (232, 252, 248),
        "plate": (10, 28, 34),
    },
    INK: {
        "wing": (226, 226, 228),
        "wing_calm": (176, 176, 184),
        "vein": (255, 255, 255),
        "body": (28, 28, 34),
        "core": (246, 246, 248),
        "edge": (150, 150, 160),
        "ring": (226, 226, 226),
        "text": (246, 246, 246),
        "plate": (16, 16, 20),
    },
    MOSS: {
        "wing": (176, 224, 150),
        "wing_calm": (150, 200, 170),
        "vein": (240, 255, 232),
        "body": (30, 50, 34),
        "core": (234, 255, 214),
        "edge": (120, 178, 92),
        "ring": (196, 232, 168),
        "text": (240, 250, 232),
        "plate": (16, 28, 20),
    },
    ROSE: {
        "wing": (255, 178, 196),
        "wing_calm": (226, 160, 210),
        "vein": (255, 240, 246),
        "body": (62, 30, 48),
        "core": (255, 226, 236),
        "edge": (232, 120, 154),
        "ring": (255, 196, 212),
        "text": (255, 242, 246),
        "plate": (34, 16, 26),
    },
    DUSK: {
        "wing": (166, 154, 236),
        "wing_calm": (134, 148, 220),
        "vein": (236, 232, 255),
        "body": (30, 28, 62),
        "core": (230, 226, 255),
        "edge": (118, 112, 200),
        "ring": (186, 178, 248),
        "text": (238, 234, 255),
        "plate": (18, 16, 38),
    },
    FROST: {
        "wing": (186, 228, 248),
        "wing_calm": (198, 214, 244),
        "vein": (244, 252, 255),
        "body": (30, 44, 58),
        "core": (236, 250, 255),
        "edge": (128, 188, 218),
        "ring": (206, 238, 252),
        "text": (240, 250, 255),
        "plate": (16, 26, 34),
    },
    EMBER: {
        "wing": (255, 154, 112),
        "wing_calm": (236, 138, 128),
        "vein": (255, 232, 216),
        "body": (58, 24, 30),
        "core": (255, 220, 186),
        "edge": (224, 96, 64),
        "ring": (255, 186, 148),
        "text": (255, 240, 230),
        "plate": (30, 12, 16),
    },
}

# --------------------------------------------------------------------------
# Coats: a tint mixed into a buddy's own colours, so a rose cat still reads as
# a cat. ``natural`` leaves the built-in palette untouched.
# --------------------------------------------------------------------------

NATURAL = "natural"

COAT_ORDER = (
    NATURAL,
    "midnight",
    "cocoa",
    "rose",
    "mint",
    "lavender",
    "ash",
    "gold",
    "pearl",
)

COAT_LABELS = {
    NATURAL: "Natural",
    "midnight": "Midnight",
    "cocoa": "Cocoa",
    "rose": "Rose",
    "mint": "Mint",
    "lavender": "Lavender",
    "ash": "Ash",
    "gold": "Gold",
    "pearl": "Pearl",
}

# coat id -> (tint RGB, strength)
_COAT_TINT: dict[str, tuple[tuple[int, int, int], float]] = {
    "midnight": ((58, 66, 118), 0.5),
    "cocoa": ((124, 84, 58), 0.42),
    "rose": ((235, 126, 152), 0.38),
    "mint": ((110, 204, 158), 0.42),
    "lavender": ((164, 134, 232), 0.42),
    "ash": ((126, 128, 138), 0.5),
    "gold": ((232, 182, 84), 0.38),
    "pearl": ((250, 246, 240), 0.46),
}


def mix(rgb: tuple[int, int, int], tint: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    """Blend ``rgb`` toward ``tint`` by ``amount`` (0..1)."""
    amount = max(0.0, min(1.0, amount))
    return (
        int(round(rgb[0] + (tint[0] - rgb[0]) * amount)),
        int(round(rgb[1] + (tint[1] - rgb[1]) * amount)),
        int(round(rgb[2] + (tint[2] - rgb[2]) * amount)),
    )


def coat_look(coat: str) -> tuple[tuple[int, int, int], float] | None:
    return _COAT_TINT.get(coat)


def tint_rgb(rgb: tuple[int, int, int], coat: str, scale: float = 1.0) -> tuple[int, int, int]:
    look = _COAT_TINT.get(coat)
    if look is None:
        return rgb
    tint, amount = look
    return mix(rgb, tint, amount * scale)


def recolour(character, coat: str):
    """A copy of a buddy with the coat mixed in. Trim stays dark enough to read."""
    if coat not in _COAT_TINT:
        return character
    tint, amount = _COAT_TINT[coat]
    return replace(
        character,
        body=mix(character.body, tint, amount),
        trim=mix(character.trim, tint, amount * 0.28),
        accent=mix(character.accent, tint, amount * 0.75),
    )


def tinted_palette(colors: dict[str, tuple[int, int, int]], coat: str) -> dict[str, tuple[int, int, int]]:
    """The glass palette nudged toward a coat, for the moth's lantern."""
    look = _COAT_TINT.get(coat)
    if look is None:
        return colors
    tint, amount = look
    warm = (255, 246, 232)
    return {
        key: mix(value, tint if key not in ("text", "vein") else warm, amount * 0.35)
        for key, value in colors.items()
    }
