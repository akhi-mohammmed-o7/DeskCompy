"""Load user-authored buddies from disk, defensively.

A custom buddy is a folder whose *folder name* is the safe id, containing a
``buddy.json``. Nothing in the manifest is trusted: it is size-capped, parsed
with the stdlib JSON reader (never evaluated), every string is cleaned and
length-capped, colours must be plain hex, the body shape must be one of the
eight drawn bodies, and dialogue is only accepted for known situations.

Images, if present, are loaded by :mod:`sprites`, which rejects oversized
files and huge dimensions before decoding. A manifest can never name a path:
the folder is discovered by listing, and the id must match a strict slug
pattern, so ``../`` and drive letters cannot get through.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from characters import BUILTIN_KEYS, CHARACTERS, Character
from paths import asset_dirs, buddies_dir
from safety import clean_slug, clean_text, hex_colour
from chatter import SITUATIONS

log = logging.getLogger("lumen")

MANIFEST = "buddy.json"
MAX_MANIFEST_BYTES = 32 * 1024
MAX_NAME = 16
MAX_SPECIES = 24
MAX_TAGLINE = 70
MAX_LINE = 90
MAX_LINES_PER_SITUATION = 6
MAX_TOTAL_LINES = 60

TEMPLATE_MANIFEST = """{
  "name": "Bean",
  "species": "desk bean",
  "tagline": "small, round, emotionally supportive",
  "shape": "cat",
  "body": "#f6dcc4",
  "trim": "#6b4d52",
  "accent": "#ffb08c",
  "lines": {
    "poke": ["Boop. I am legally a bean now."],
    "chill": ["We are doing nothing. It is going great."]
  }
}
"""

README = """Your own buddy
==============

Make a folder here, named with lowercase letters, numbers, - or _ (for
example: bean). Put a buddy.json inside it:

  buddy.json     the only required file
  calm.png       optional art: calm.png, working.png, scatter.png,
  working.png    sleeping.png, focus.png, or companion.png
  scatter.png    numbered frames work too: working_0.png, working_1.png...
  sleeping.png
  focus.png

buddy.json fields:

  name      required, up to 16 characters
  species   up to 24 characters
  tagline   up to 70 characters
  shape     one of: moth, cat, frog, ghost, axolotl, dog, bunny, owl
            (used until art exists)
  body      optional #rrggbb colour for the drawn body
  trim      optional #rrggbb colour for outlines
  accent    optional #rrggbb colour for cheeks and details
  lines     optional kind -> list of lines. Kinds include:
            meet, study, game, work, chill, away, back, poke, late, long,
            focus_start, focus_done, water, click, type, work_tired, fun,
            study_grind, game_hype, smalltalk

Then choose Reload custom buddies from the companion menu. Files are local;
the app never downloads or executes anything from this folder. Images are
rejected if they are over 4 MB or larger than 2048 x 2048, and text is capped
and stripped of invisible control characters.
"""


def custom_dirs() -> list[Path]:
    """Where manifests and art live, most personal first."""
    roots = [buddies_dir()]
    for assets in asset_dirs():
        roots.append(assets / "custom")
    return roots


def _base_character(shape: str) -> Character:
    if shape in BUILTIN_KEYS:
        return CHARACTERS[shape]
    return CHARACTERS["moth"]


def _clean_lines(raw: object) -> dict[str, tuple[str, ...]]:
    if not isinstance(raw, dict):
        return {}
    accepted: dict[str, tuple[str, ...]] = {}
    total = 0
    for situation in SITUATIONS:
        values = raw.get(situation)
        if not isinstance(values, list):
            continue
        lines: list[str] = []
        for value in values[:MAX_LINES_PER_SITUATION]:
            text = clean_text(value, MAX_LINE)
            if text and text not in lines:
                lines.append(text)
        if lines:
            accepted[situation] = tuple(lines)
            total += len(lines)
        if total >= MAX_TOTAL_LINES:
            break
    return accepted


def _read_manifest(folder: Path) -> dict | None:
    manifest = folder / MANIFEST
    try:
        if manifest.is_symlink() or not manifest.is_file():
            return None
        if manifest.stat().st_size > MAX_MANIFEST_BYTES:
            log.warning("Ignoring oversized buddy manifest: %s", manifest)
            return None
        raw = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        # JSONDecodeError is a ValueError. Deeply nested input is bounded by
        # the byte cap but can still trip the parser's recursion guard.
        log.warning("Ignoring unreadable buddy manifest %s: %s", manifest, exc)
        return None
    return raw if isinstance(raw, dict) else None


def _character_from(folder: Path, data: dict) -> Character | None:
    slug = clean_slug(folder.name)
    if not slug or slug in BUILTIN_KEYS:
        return None
    shape = data.get("shape")
    shape = shape if isinstance(shape, str) and shape in BUILTIN_KEYS else "moth"
    base = _base_character(shape)
    name = clean_text(data.get("name"), MAX_NAME) or slug.replace("_", " ").title()
    species = clean_text(data.get("species"), MAX_SPECIES, fallback="custom buddy")
    tagline = clean_text(data.get("tagline"), MAX_TAGLINE, fallback=base.tagline)
    body = hex_colour(data.get("body")) or base.body
    trim = hex_colour(data.get("trim")) or base.trim
    accent = hex_colour(data.get("accent")) or base.accent
    return Character(
        key=slug,
        name=name,
        species=species,
        tagline=tagline,
        body=body,
        trim=trim,
        accent=accent,
        shape=shape,
        lines=_clean_lines(data.get("lines")),
        custom=True,
    )


def load_custom_buddies(folders: list[Path] | None = None) -> dict[str, Character]:
    """All valid custom buddies, first folder winning on duplicate ids."""
    found: dict[str, Character] = {}
    roots = custom_dirs() if folders is None else [Path(folder) for folder in folders]
    for root in roots:
        try:
            if not root.is_dir():
                continue
            entries = sorted(root.iterdir(), key=lambda item: item.name.lower())
        except OSError as exc:
            log.warning("Could not read buddy folder %s: %s", root, exc)
            continue
        for folder in entries:
            try:
                if folder.is_symlink() or not folder.is_dir():
                    continue
            except OSError:
                continue
            slug = clean_slug(folder.name)
            if not slug or slug in BUILTIN_KEYS or slug in found:
                continue
            data = _read_manifest(folder)
            if data is None:
                continue
            buddy = _character_from(folder, data)
            if buddy is not None:
                found[buddy.key] = buddy
    return found


def install_custom_buddies(folders: list[Path] | None = None) -> dict[str, Character]:
    """Load validated buddies and put them on the roster."""
    from characters import install_custom

    buddies = load_custom_buddies(folders)
    install_custom(buddies)
    return buddies


def make_template(root: Path | None = None) -> Path:
    """Create the user buddy folder and a non-loading template, never clobbering."""
    target = buddies_dir() if root is None else Path(root)
    target.mkdir(parents=True, exist_ok=True)
    readme = target / "README.txt"
    if not readme.exists():
        readme.write_text(README, encoding="utf-8")
    template = target / "_template"
    template.mkdir(exist_ok=True)
    example = template / MANIFEST
    if not example.exists():
        example.write_text(TEMPLATE_MANIFEST, encoding="utf-8")
    return target
