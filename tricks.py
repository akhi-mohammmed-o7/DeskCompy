"""Predefined performances the buddy can do on its own.

A trick is pure geometry: given a progress value between 0 and 1 and an
amplitude, it returns a window offset, a body spin, and a sparkle strength.
``gesture`` names the character-shaped overlay the painter should draw on top
(flapping wings, a licking tongue, splashing water) so each buddy performs in
its own idiom. The window owns the timing, the screen clamping, and the choice
of where a dash lands, so this module stays testable without Qt.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Trick:
    key: str
    duration: float
    gesture: str = ""
    # Some tricks only make sense beside a screen edge.
    edge_only: bool = False


HOP = Trick("hop", 2.2)
SOMERSAULT = Trick("somersault", 1.7)
DASH = Trick("dash", 2.8)
PEEK = Trick("peek", 3.0, edge_only=True)
ORBIT = Trick("orbit", 2.6)
WIGGLE = Trick("wiggle", 1.8)
FLUTTER = Trick("flutter", 3.2, "flutter")
GROOM = Trick("groom", 3.4, "groom")
SPLASH = Trick("splash", 2.8, "splash")
CROAK = Trick("croak", 2.4, "croak")
FLICKER = Trick("flicker", 2.6, "flicker")
BINKY = Trick("binky", 2.0, "binky")

TRICKS: tuple[Trick, ...] = (
    HOP,
    SOMERSAULT,
    DASH,
    PEEK,
    ORBIT,
    WIGGLE,
    FLUTTER,
    GROOM,
    SPLASH,
    CROAK,
    FLICKER,
    BINKY,
)

# Each body does the things that body would actually do. Anything unknown
# (a custom buddy borrowing a body) falls back to that body's list.
CHARACTER_TRICKS: dict[str, tuple[Trick, ...]] = {
    "moth": (FLUTTER, ORBIT, PEEK, SOMERSAULT, DASH),
    "owl": (FLUTTER, ORBIT, PEEK, GROOM, DASH),
    "cat": (GROOM, WIGGLE, DASH, HOP, PEEK),
    "dog": (GROOM, DASH, HOP, WIGGLE, SOMERSAULT),
    "bunny": (BINKY, GROOM, DASH, HOP, PEEK),
    "frog": (CROAK, HOP, WIGGLE, PEEK),
    "ghost": (FLICKER, ORBIT, PEEK, SOMERSAULT),
    "axolotl": (SPLASH, WIGGLE, ORBIT, PEEK),
}


def tricks_for(shape: str) -> tuple[Trick, ...]:
    """The performance list for a body shape."""
    return CHARACTER_TRICKS.get(shape, (HOP, WIGGLE, PEEK, ORBIT))


def envelope(progress: float) -> float:
    """One smooth hill: zero at both ends, one in the middle."""
    progress = min(1.0, max(0.0, progress))
    return math.sin(math.pi * progress)


def _ease_out(progress: float) -> float:
    progress = min(1.0, max(0.0, progress))
    return 1.0 - (1.0 - progress) ** 3


def _ease_in_out(progress: float) -> float:
    progress = min(1.0, max(0.0, progress))
    return progress * progress * (3.0 - 2.0 * progress)


def sample(
    key: str,
    progress: float,
    amplitude: tuple[float, float] = (0.0, 0.0),
) -> tuple[float, float, float, float]:
    """``(dx, dy, spin_degrees, sparkle)`` for this trick at ``progress``.

    Every trick except ``dash`` returns to its starting point at the end, so
    the buddy never wanders off without meaning to. A dash deliberately ends
    somewhere new and the amplitude is the full travel distance.
    """
    amp_x, amp_y = amplitude
    sparkle = envelope(progress)
    if key == HOP.key:
        # Three quick bounces, each one a little shorter than the last.
        hops = abs(math.sin(3.0 * math.pi * progress))
        return 0.0, -amp_y * hops, 0.0, sparkle
    if key == SOMERSAULT.key:
        return 0.0, -amp_y * sparkle, 360.0 * _ease_in_out(progress), sparkle
    if key == DASH.key:
        return amp_x * _ease_out(progress), amp_y * _ease_out(progress), 0.0, sparkle
    if key == PEEK.key:
        return amp_x * sparkle, 0.0, 0.0, sparkle
    if key == ORBIT.key:
        angle = math.tau * progress
        return (
            amp_x * (math.cos(angle) - 1.0),
            amp_y * math.sin(angle),
            math.sin(angle) * 5.0,
            sparkle,
        )
    if key == WIGGLE.key:
        return (
            amp_x * math.sin(6.0 * math.pi * progress) * sparkle,
            0.0,
            math.sin(8.0 * math.pi * progress) * 6.0,
            sparkle,
        )
    # Gesture tricks keep the perch still and let the body do the talking.
    return 0.0, 0.0, 0.0, sparkle
