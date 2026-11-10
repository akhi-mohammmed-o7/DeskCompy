"""Locations that stay valid both from source and inside a PyInstaller build.

Images are resolved in two places, in this order:

1. An ``assets`` folder sitting beside the .exe (or beside these sources).
   That is the folder a person can open and swap files in after packaging.
2. The copy bundled inside the executable, if there is one.

The first hit wins, so a shipped image never blocks a replacement.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "DeskCompy"
VERSION = "1.4.0"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def install_root() -> Path:
    """Folder the user can actually find: next to the exe, or the project root."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def bundle_root() -> Path:
    meipass = getattr(sys, "_MEIPASS", None)
    if is_frozen() and meipass:
        return Path(meipass)
    return install_root()


def asset_dirs() -> list[Path]:
    ordered: list[Path] = []
    for folder in (install_root() / "assets", bundle_root() / "assets"):
        if folder not in ordered:
            ordered.append(folder)
    return ordered


def config_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        folder = Path(appdata) / "DeskCompy"
    else:
        folder = Path.home() / ".config" / "deskcompy"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def settings_file() -> Path:
    return config_dir() / "settings.json"


def buddies_dir() -> Path:
    """User-owned custom buddies. Safe to write to after packaging."""
    folder = config_dir() / "buddies"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


