"""Start DeskCompy with Windows, only when the user asks for it.

The entry is one value under ``HKCU\\...\\Run``, so it is per-user, needs no
administrator rights, and the same switch removes it again. On other platforms
nothing is written and the switch reports that it is unsupported.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from paths import is_frozen

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "DeskCompy"
log = logging.getLogger("lumen")


def supported() -> bool:
    return sys.platform == "win32"


def _registry():
    if not supported():
        return None
    try:
        import winreg
    except ImportError:  # pragma: no cover - only on non-Windows builds
        return None
    return winreg


def command() -> str:
    """The quoted command Windows should run at sign-in.

    A frozen build points at the executable itself. From source it points at
    the matching ``pythonw.exe`` so no console window flashes up, with
    ``main.py`` as its argument.
    """
    if is_frozen():
        return f'"{Path(sys.executable).resolve()}"'
    executable = Path(sys.executable).resolve()
    if executable.name.lower() == "python.exe":
        windowless = executable.with_name("pythonw.exe")
        if windowless.exists():
            executable = windowless
    main = Path(__file__).resolve().with_name("main.py")
    return f'"{executable}" "{main}"'


def is_enabled() -> bool:
    """True only when the stored command is the one this copy would write."""
    winreg = _registry()
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _kind = winreg.QueryValueEx(key, VALUE_NAME)
    except OSError:
        return False
    return isinstance(value, str) and value.strip() == command()


def set_enabled(enabled: bool) -> bool:
    """Add or remove the entry. Returns whether the registry now agrees."""
    winreg = _registry()
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            if enabled:
                winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, command())
            else:
                try:
                    winreg.DeleteValue(key, VALUE_NAME)
                except FileNotFoundError:
                    pass
    except OSError as exc:
        log.warning("Could not update the startup entry: %s", exc)
        return False
    return is_enabled() == enabled
