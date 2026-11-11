# Contributing to DeskCompy

Thanks for wanting to make the desk a little friendlier. This project is a
single-process PyQt6 app with no network layer; keep it that way unless a
change is explicitly about adding one.

## Set up

```bash
git clone https://github.com/akhi-mohammmed-o7/DeskCompy.git
cd DeskCompy
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Requires Python 3.10+ and runs primarily on Windows 10/11. The UI and art are
Qt-only, so Linux/macOS mostly work from source, but global input hooks and the
start-with-Windows toggle are Windows-specific and untested elsewhere.

## Test before you push

```bash
python -m unittest discover -s tests
```

CI runs the same suite on Windows for Python 3.10 and 3.12 with
`QT_QPA_PLATFORM=offscreen`. Please keep tests headless: no real timers, no
audio playback, no global hooks. Monkeypatch `settings_store.settings_file` to
a temporary path whenever a test loads or saves settings.

Adding a test for a new rule is expected. A bug fix without a regression test
is usually not ready.

## Code style

- Python 3.10+, standard library first. New third-party dependencies need a
  reason and a mention in `requirements.txt`.
- Type hints on public functions, short docstrings on modules and non-obvious
  helpers, `from __future__ import annotations` where the file already uses it.
- Keep painting in `painter.py`, state/persistence in `settings_store.py`, and
  window/menu wiring in `ui_engine.py`.
- No network calls, no reading key values, window titles, or screen contents.
- Text that a user can supply must go through `safety.clean_text`; file paths
  must stay inside the user buddy folder.

## Common changes

**A new accessory.** Add an `Accessory(...)` row in `rewards.py` (style is one
of `hat`, `face`, `neck`, `back`, `above`), draw its `key` inside
`_draw_accessory` in `painter.py` following the existing anchors, and extend
`tests/test_rewards.py`. Neckwear must be added to the `neckwear` tuple so it
tucks behind a book or laptop; back items draw before the body.

**A new buddy.** Add a `Character` to `characters.py`, give it a body drawer in
`painter.py`, and add its name/dialogue. Update `BUILTIN_KEYS`, the roster
screenshot in `docs/screenshots/`, and run the buddy tests.

**A new sound.** Add a key to `sounds._KEYS` and a synthesis branch in
`sounds.build`; `tests/test_focus_log.py` verifies every cue is a valid WAV.

**A new activity rule.** Keep it cadence-only, update `activity.py` and
`tests/test_rhythm.py`, and document the behaviour in the README.

## Pull requests

- One focused change per PR, with a clear description of the behaviour change.
- Say what you tested and on which OS. Screenshots/GIFs are welcome for visual
  changes.
- Do not commit `settings.json`, generated WAVs, `_preview_*.png` scratch art,
  or build output — they are ignored.
- By contributing you agree your work is licensed under the project's MIT
  license.

## Reporting bugs

Include the DeskCompy version (`paths.VERSION`), Windows version, Python
version when running from source, and the console output if you started it
from a terminal. For visual bugs, a screenshot helps. For privacy-sensitive
reports, do not paste your settings file; it contains only preferences.
