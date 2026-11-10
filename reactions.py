"""Live mirroring: the buddy types when you type and clicks when you click.

Nothing here records real keystrokes. A burst of input only creates decorative
little keycaps with made-up letters, plus rings for a click. The buddy uses the
same pulses to bob its head and squash its body, which is what makes the desk
feel shared rather than observed.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen

# Made-up characters for the floating "keys". Deliberately not your input.
GLYPHS = "aeioukybm?!;:>_#"
MAX_KEYCAPS = 18
MAX_RIPPLES = 4
KEYCAP_LIFE = (0.85, 1.4)


@dataclass
class _Keycap:
    dx: float
    dy: float
    vx: float
    vy: float
    age: float
    life: float
    glyph: str


@dataclass
class _Ripple:
    dx: float
    dy: float
    age: float
    life: float


class Mirror:
    """A tiny particle system sized for a 200 px window."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()
        self._caps: list[_Keycap] = []
        self._ripples: list[_Ripple] = []
        self._typing = 0.0
        self._clicking = 0.0

    # --- input ---------------------------------------------------------

    def typed(self, count: int = 1) -> None:
        count = max(1, min(3, int(count)))
        for _ in range(count):
            life = self._rng.uniform(*KEYCAP_LIFE)
            self._caps.append(
                _Keycap(
                    dx=self._rng.uniform(-34, 34),
                    dy=self._rng.uniform(2, 24),
                    vx=self._rng.uniform(-9, 9),
                    vy=self._rng.uniform(-30, -20),
                    age=0.0,
                    life=life,
                    glyph=self._rng.choice(GLYPHS),
                )
            )
        if len(self._caps) > MAX_KEYCAPS:
            del self._caps[: len(self._caps) - MAX_KEYCAPS]
        self._typing = min(1.0, self._typing + 0.22 * count)

    def clicked(self) -> None:
        self._ripples.append(
            _Ripple(
                dx=self._rng.uniform(-26, 26),
                dy=self._rng.uniform(30, 42),
                age=0.0,
                life=0.52,
            )
        )
        if len(self._ripples) > MAX_RIPPLES:
            del self._ripples[: len(self._ripples) - MAX_RIPPLES]
        self._clicking = 1.0

    def clear(self) -> None:
        self._caps.clear()
        self._ripples.clear()
        self._typing = 0.0
        self._clicking = 0.0

    # --- time ----------------------------------------------------------

    def advance(self, seconds: float) -> None:
        dt = max(0.0, min(0.1, float(seconds)))
        for cap in self._caps:
            cap.age += dt
            cap.dx += cap.vx * dt
            cap.dy += cap.vy * dt
            cap.vy += 26.0 * dt
        self._caps = [cap for cap in self._caps if cap.age < cap.life]
        for ripple in self._ripples:
            ripple.age += dt
        self._ripples = [ripple for ripple in self._ripples if ripple.age < ripple.life]
        self._typing *= math.exp(-dt / 0.85)
        self._clicking *= math.exp(-dt / 0.22)
        if self._typing < 0.002:
            self._typing = 0.0
        if self._clicking < 0.002:
            self._clicking = 0.0

    @property
    def typing(self) -> float:
        return min(1.0, self._typing)

    @property
    def clicking(self) -> float:
        return min(1.0, self._clicking)

    @property
    def busy(self) -> bool:
        return bool(self._caps or self._ripples)

    # --- drawing -------------------------------------------------------

    def draw(
        self,
        painter: QPainter,
        cx: float,
        cy: float,
        accent: tuple[int, int, int],
        text: tuple[int, int, int],
    ) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        for ripple in self._ripples:
            t = min(1.0, ripple.age / ripple.life)
            radius = 6.0 + 26.0 * t
            alpha = int(190 * (1.0 - t))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(accent[0], accent[1], accent[2], alpha), 1.6))
            painter.drawEllipse(QPointF(cx + ripple.dx, cy + ripple.dy), radius, radius * 0.55)

        font = QFont("Segoe UI", 5)
        font.setBold(True)
        painter.setFont(font)
        for cap in self._caps:
            left = 1.0 - min(1.0, cap.age / cap.life)
            alpha = int(235 * left)
            box = QRectF(cx + cap.dx - 4.0, cy + cap.dy - 4.0, 8.0, 8.0)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(accent[0], accent[1], accent[2], int(alpha * 0.55)))
            painter.drawRoundedRect(box, 2.2, 2.2)
            painter.setPen(QPen(QColor(text[0], text[1], text[2], alpha), 1.0))
            painter.drawText(box, Qt.AlignmentFlag.AlignCenter, cap.glyph)
        painter.restore()
