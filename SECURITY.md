# Security notes

DeskCompy is a local desktop toy. It is designed so that nothing it watches,
loads, or draws can turn into a path, a command, or a network request.

## What the app touches

- **Input is counts only.** The global hooks record *when* a key or mouse
  button goes down. The character is never read, held-key repeat is ignored,
  and nothing about your typing is written to disk. Cadence is folded into an
  activity guess a few times a second.
- **No network.** There are no HTTP clients, sockets, telemetry, or update
  checks in the code. The only file writes are `settings.json`, the optional
  user buddy folder, and (when you press the button) a template manifest.
- **Chat stays local.** Questions are cleaned and matched against fixed keyword
  rules; answers come from static tables. The open chat panel holds a short
  transcript in memory and clears it when closed. Nothing is logged, saved,
  or sent anywhere. There is no model and no API call.

## Untrusted text

Any text a person can supply — nickname, intention line, buddy manifest,
custom dialogue — goes through `safety.clean_text`:

- control, format, and bidirectional-override characters are removed, so an
  invisible override cannot disguise a short string as something else;
- tabs and newlines become spaces, whitespace collapses, and the result is
  length-capped per surface (16 characters for a nickname, 70 for a tagline,
  80 for an intention, 90 for a dialogue line, 120 for a question).

Rendering never treats that text as markup. The speech bubble and caption paint
plain strings with `QPainter`. Qt renders *tooltips* as rich text, so every
tooltip built from buddy data is passed through `html.escape` first.

## Untrusted files

Custom buddies live in `%APPDATA%\DeskCompy\buddies` (or `assets\custom` beside
the app). Loading them is deliberately narrow:

- the **folder name is the id** and must match `[a-z][a-z0-9_-]{1,23}`;
  symlinks and non-directories are skipped, and an id that collides with a
  built-in is dropped. A manifest can never name a path, so `..`, drive
  letters, and UNC prefixes cannot reach the loader;
- `buddy.json` must be a regular file no larger than 32 KB, parsed with the
  stdlib `json` reader. Nothing is ever evaluated or imported;
- colours must be plain `#rrggbb`; an unknown body shape falls back to the
  drawn moth; dialogue is accepted only for known situations, with per-line
  and per-situation caps;
- images are rejected before decoding when they exceed 4 MB, are symlinks, or
  report a size over 1024×1024. A numbered sequence stops at 24 frames or a
  24-megapixel budget. This blocks decompression bombs.

A broken or hostile manifest is skipped and logged; it can never stop the app
from starting or take over an existing buddy.

## Local privilege

The app runs with the same rights as the user, adds no autostart entry, and
installs nothing. Ghost perch (click-through) is refused when no tray icon
exists, because that would otherwise be a way to lock the window away with no
way back.
