"""A soft two-note chime, synthesised in memory and cached.

No audio file ships with the app, so there is nothing to find, move, or break
after packaging. The WAV is written once to the settings folder (or the temp
folder) because Windows' standard library will only play a file
asynchronously, not a memory image. Elsewhere ``play`` returns False and the
caller falls back to the system beep.
"""

from __future__ import annotations

import io
import logging
import math
import struct
import tempfile
import wave
from pathlib import Path

log = logging.getLogger("lumen")

_SAMPLE_RATE = 22_050
# (frequency, start seconds, length seconds) — a fifth, C5 then G5.
_NOTES = ((523.25, 0.00, 0.62), (783.99, 0.17, 0.86))
_TOTAL = 1.05
_PEAK = 0.20

_cache: bytes | None = None
_unavailable = False
_file: Path | None = None


def _build() -> bytes:
    frames = bytearray()
    total_frames = int(_SAMPLE_RATE * _TOTAL)
    for index in range(total_frames):
        t = index / _SAMPLE_RATE
        sample = 0.0
        for frequency, start, length in _NOTES:
            local = t - start
            if local < 0 or local >= length:
                continue
            # 40 ms attack, exponential tail: a chime, not a beep.
            attack = min(1.0, local / 0.04)
            decay = math.exp(-3.1 * (local / length))
            sample += math.sin(2 * math.pi * frequency * local) * attack * decay
        sample = max(-1.0, min(1.0, sample * _PEAK))
        frames += struct.pack("<h", int(sample * 32767))

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(_SAMPLE_RATE)
        wav.writeframes(bytes(frames))
    return buffer.getvalue()


def _write(data: bytes) -> Path | None:
    """Keep one cached WAV on disk. Rewriting while it plays would fail on Windows."""
    global _file
    if _file is not None and _file.is_file() and _file.stat().st_size == len(data):
        return _file
    folders: list[Path] = []
    try:
        from paths import settings_file

        folders.append(settings_file().parent)
    except Exception:
        log.debug("No settings folder for the chime", exc_info=True)
    folders.append(Path(tempfile.gettempdir()))
    for folder in folders:
        target = folder / "lumen-chime.wav"
        try:
            temporary = target.with_suffix(".wav.tmp")
            temporary.write_bytes(data)
            temporary.replace(target)
            _file = target
            return target
        except OSError:
            continue
    return None


def play() -> bool:
    """Start the chime without blocking. True when something was played."""
    global _cache, _unavailable
    if _unavailable:
        return False
    try:
        import winsound
    except ImportError:
        _unavailable = True
        return False
    try:
        if _cache is None:
            _cache = _build()
        path = _write(_cache)
        if path is None:
            _unavailable = True
            return False
        winsound.PlaySound(
            str(path),
            winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
        )
        return True
    except Exception:
        log.warning("The chime could not play; falling back to the system beep.", exc_info=True)
        _unavailable = True
        return False
