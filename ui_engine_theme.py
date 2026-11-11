"""One source of truth for the window's palette and text colours.

The window is the screen frame the buddy sits in: backdrop, shadow, glow, ring,
caption, plate, tooltips, and focus-ring. This module is the source of truth for
those colours so the README screenshots, the theme shell, and any future skin
all agree with what the buddy actually draws.

Defaults match the body palette the window caps at when a glass theme is chosen,
so switching palettes changes both the buddy and the window together.
"""

from __future__ import annotations

from PyQt6.QtGui import QColor

# Background palette the window falls back to when nothing quieter is chosen.
_BACK = {
    "dark": QColor(32, 32, 54),
    "mid": QColor(54, 54, 86),
    "light": QColor(86, 86, 130),
}

MENU_QSS = """
QMenu {
    background-color: rgba(22, 16, 34, 235);
    color: #f6f1e8;
    border: 1px solid rgba(255, 214, 160, 80);
    border-radius: 10px;
    padding: 6px;
}
QMenu::item {
    padding: 6px 18px;
    border-radius: 6px;
    background: transparent;
}
QMenu::item:selected {
    background-color: rgba(255, 176, 90, 55);
}
QMenu::item:disabled {
    color: rgba(246, 241, 232, 150);
}
QMenu::separator {
    height: 1px;
    background: rgba(255, 255, 255, 28);
    margin: 5px 10px;
}
"""


def shell_palette() -> dict[str, QColor]:
    """Palette entry for the 3x3 shell grid."""
    return {
        "dark": QColor(32, 32, 54),
        "mid": QColor(54, 54, 86),
        "light": QColor(86, 86, 130),
    }


def pop_accent() -> QColor:
    return QColor(255, 176, 90)


def window_color(style: str = "dark") -> QColor:
    return _BACK[style]
