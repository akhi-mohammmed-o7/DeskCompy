"""One source of truth for the window's config.

Reads the body palette from `theme.py` and re-exposes it for the app's config.\nProvides a few high-level constants the window uses to decide which windows to\nshow (e.g. when to fall back to the system palette).\n"""

from __future__ import annotations

from theme import PALETTE_ORDER, PALETTE_LABELS
from ui_engine_theme import shell_palette, pop_accent

# Default palette for the window when no glass theme is chosen.
BODY_PALETTE = "amber"

DEFAULT_SHELL_PALETTE = shell_palette()

# Backdrop gradient colours used by the window's dark gradient.
BACK_COLORS = ["dark", "mid", "light"]


def active_palette() -> str:
    """Return the active palette name for the window."""
    return BODY_PALETTE


def window_styles() -> list[str]:
    return BACK_COLORS


def accent() -> tuple[int, int, int]:
    """RGB accent colour for the window's pop colour."""
    c = pop_accent()
    return (c.red(), c.green(), c.blue())
