"""Small, boring rules that every user-supplied string passes through.

The buddy has two untrusted surfaces: text a person types into the talk box or
the customization dialog, and a ``buddy.json`` manifest they drop on disk. None
of it is markup, a path, or a filename. Keeping the rules here means the UI and
the asset loader cannot drift apart, and tests can hit them without Qt.

What this does *not* try to do is sanitise HTML for a browser. The app never
renders user text as rich text: the speech bubble paints a plain string and
every tooltip built from a manifest is escaped. Stripping control and
bidirectional characters is still worth doing, because invisible override
characters can make a seven-character nickname look like something else.
"""

from __future__ import annotations

import re
import unicodedata

SLUG_RE = re.compile(r"[a-z][a-z0-9_-]{1,23}\Z")
CONTROL_CATEGORIES = {"Cc", "Cf", "Cs", "Co", "Cn", "Zl", "Zp"}


def clean_text(value: object, max_length: int = 80, *, fallback: str = "") -> str:
    """One line of human-readable text, bounded and stripped of controls.

    Tabs and newlines become spaces, invisible format characters are dropped,
    runs of whitespace collapse, and the result is cut to ``max_length``.
    """
    if not isinstance(value, str):
        return fallback
    limit = max(0, int(max_length))
    pieces: list[str] = []
    for char in value:
        if char in "\r\n\t":
            pieces.append(" ")
            continue
        if unicodedata.category(char) in CONTROL_CATEGORIES:
            continue
        pieces.append(char)
    text = " ".join("".join(pieces).split())
    text = text.strip()
    if limit and len(text) > limit:
        text = text[:limit].rstrip()
    return text or fallback


def clean_slug(value: object) -> str:
    """A folder-safe buddy id, or an empty string when it is not safe."""
    if not isinstance(value, str):
        return ""
    return value if SLUG_RE.fullmatch(value) else ""


def hex_colour(value: object) -> tuple[int, int, int] | None:
    """``#rrggbb`` / ``rrggbb`` to an RGB tuple. Anything else is ignored."""
    if not isinstance(value, str):
        return None
    text = value.strip().lstrip("#")
    if len(text) != 6 or any(char not in "0123456789abcdefABCDEF" for char in text):
        return None
    return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)
