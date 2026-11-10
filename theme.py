"""Three glass palettes. No Qt imports, so settings can validate names cheaply."""

from __future__ import annotations

AMBER = "amber"
TIDE = "tide"
INK = "ink"

PALETTE_ORDER = (AMBER, TIDE, INK)

PALETTE_LABELS = {
    AMBER: "Amber lantern",
    TIDE: "Tide glass",
    INK: "Ink",
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
}
