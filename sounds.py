"""Small, soft cues synthesised in memory: focus ticks and character gestures.

No audio files ship with the app. Each cue is a few hundred milliseconds of
shaped sine/noise, written once to the settings folder because Windows can only
play a file asynchronously. On other platforms ``play`` returns False and the
caller stays silent; the app never depends on a cue being heard.
"""

from __future__ import annotations

import io
import logging
import math
import random
import struct
import tempfile
import wave
from pathlib import Path

log = logging.getLogger("lumen")

_SAMPLE_RATE = 22_050
_KEYS = (
    "tick",
    "flutter",
    "groom",
    "splash",
    "croak",
    "flicker",
    "binky",
)

_cache: dict[str, bytes] = {}
_files: dict[str, Path] = {}
_unavailable = False


def _envelope(t: float, length: float, attack: float = 0.012) -> float:
    """Quick attack, exponential tail."""
    if t < 0 or t >= length:
        return 0.0
    rise = min(1.0, t / max(0.001, attack))
    return rise * math.exp(-3.2 * (t / length))


def _wav(frames: bytearray) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(_SAMPLE_RATE)
        wav.writeframes(bytes(frames))
    return buffer.getvalue()


def _render(length: float, voice) -> bytes:
    frames = bytearray()
    for index in range(int(_SAMPLE_RATE * length)):
        t = index / _SAMPLE_RATE
        sample = max(-1.0, min(1.0, voice(t, length)))
        frames += struct.pack("<h", int(sample * 32767))
    return _wav(frames)


def build(name: str) -> bytes:
    """WAV bytes for a cue. Pure; no audio device is touched."""
    rng = random.Random(name)
    if name == "tick":
        return _render(
            0.085,
            lambda t, length: 0.16
            * _envelope(t, length, 0.004)
            * math.sin(2 * math.pi * 1180 * t),
        )
    if name == "flutter":
        # Soft air puffs, one per wingbeat.
        return _render(
            0.52,
            lambda t, length: (
                0.085
                * _envelope(t, length, 0.03)
                * (0.55 * math.sin(2 * math.pi * 210 * t) + 0.45 * (rng.random() - 0.5))
                * (0.6 + 0.4 * math.sin(2 * math.pi * 9.5 * t))
            ),
        )
    if name == "groom":
        def voice(t: float, length: float) -> float:
            lap = math.sin(2 * math.pi * 620 * t) * _envelope(t, 0.09, 0.003)
            second = math.sin(2 * math.pi * 740 * (t - 0.17)) * _envelope(t - 0.17, 0.09, 0.003)
            return 0.12 * (lap + second)
        return _render(0.30, voice)
    if name == "splash":
        def voice(t: float, length: float) -> float:
            sweep = 760 - 430 * min(1.0, t / 0.32)
            water = math.sin(2 * math.pi * sweep * t)
            spray = (rng.random() - 0.5) * math.exp(-6.0 * t)
            return 0.10 * _envelope(t, 0.42, 0.006) * (0.7 * water + 0.5 * spray)
        return _render(0.44, voice)
    if name == "croak":
        return _render(
            0.30,
            lambda t, length: 0.11
            * _envelope(t, length, 0.02)
            * math.sin(2 * math.pi * 170 * t)
            * (0.65 + 0.35 * math.sin(2 * math.pi * 24 * t)),
        )
    if name == "flicker":
        def voice(t: float, length: float) -> float:
            sweep = 940 - 620 * (t / 0.55)
            wobble = 0.5 + 0.5 * math.sin(2 * math.pi * 6.0 * t)
            return (
                0.075
                * _envelope(t, 0.58, 0.05)
                * math.sin(2 * math.pi * sweep * t)
                * (0.35 + 0.65 * wobble)
            )
        return _render(0.58, voice)
    if name == "binky":
        def voice(t: float, length: float) -> float:
            sweep = 480 + 520 * min(1.0, t / 0.26)
            return 0.10 * _envelope(t, 0.32, 0.01) * math.sin(2 * math.pi * sweep * t)
        return _render(0.34, voice)
    raise KeyError(name)


def _file_for(name: str, data: bytes) -> Path | None:
    cached = _files.get(name)
    if cached is not None and cached.is_file() and cached.stat().st_size == len(data):
        return cached
    folders: list[Path] = []
    try:
        from paths import settings_file

        folders.append(settings_file().parent)
    except Exception:
        log.debug("No settings folder for sounds", exc_info=True)
    folders.append(Path(tempfile.gettempdir()))
    for folder in folders:
        target = folder / f"lumen-cue-{name}.wav"
        try:
            temporary = target.with_suffix(".wav.tmp")
            temporary.write_bytes(data)
            temporary.replace(target)
            _files[name] = target
            return target
        except OSError:
            continue
    return None


def play(name: str) -> bool:
    """Start a cue without blocking. False means silence, never a crash."""
    global _unavailable
    if _unavailable or name not in _KEYS:
        return False
    try:
        import winsound
    except ImportError:
        _unavailable = True
        return False
    try:
        data = _cache.get(name)
        if data is None:
            data = build(name)
            _cache[name] = data
        path = _file_for(name, data)
        if path is None:
            _unavailable = True
            return False
        winsound.PlaySound(
            str(path),
            winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
        )
        return True
    except Exception:
        log.warning("A sound cue could not play.", exc_info=True)
        _unavailable = True
        return False
