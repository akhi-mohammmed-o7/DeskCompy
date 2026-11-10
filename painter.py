"""Draw the buddy, its little desk, and the plate beneath it.

Five characters are drawn in vectors, so the app stays image-free and every
one of them can blink, breathe, slump, and bounce. A dropped image in
``assets`` still replaces the body and leaves the glow, focus ring, dew drop,
mirror particles, and caption in place.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)

from activity import AWAY, CHILL, GAMING, STUDY, WORK
from characters import Character, get as get_character
from reactions import Mirror
from states import CALM, FOCUS, SCATTER, SLEEPING, WORKING
from theme import PALETTES

CANVAS_W = 196
CANVAS_H = 232
BODY_Y = 86
PLATE_MARGIN = 14


def _mood(visual: str, activity: str) -> str:
    """A face for the moment: happy, serious, sad, or crying."""
    if visual == SLEEPING:
        return "sleep"
    if activity == AWAY:
        return "cry" if visual == SLEEPING else "sad"
    if activity in (STUDY, WORK):
        return "serious"
    if activity == GAMING or visual == SCATTER:
        return "happy"
    return "happy"


def _mood_mouth(
    painter: QPainter,
    cx: float,
    cy: float,
    mood: str,
    trim: tuple[int, int, int],
    accent: tuple[int, int, int],
    width: float = 14.0,
) -> None:
    """A tiny mouth (and tears) for the current mood."""
    painter.setBrush(Qt.BrushStyle.NoBrush)
    if mood == "happy":
        painter.setPen(QPen(_qc(trim, 220), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawArc(QRectF(cx - width / 2, cy - 2, width, 8), 200 * 16, 140 * 16)
    elif mood == "serious":
        painter.setPen(QPen(_qc(trim, 220), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(cx - width / 2 + 1, cy), QPointF(cx + width / 2 - 1, cy))
    elif mood in ("sad", "cry"):
        painter.setPen(QPen(_qc(trim, 220), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawArc(QRectF(cx - width / 2, cy - 6, width, 8), 20 * 16, 140 * 16)
        if mood == "cry":
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(_qc(accent, 190))
            for sign in (-1, 1):
                painter.drawEllipse(QPointF(cx + sign * (width / 2 - 1), cy + 5), 1.4, 2.4)


def _qc(rgb: tuple[int, int, int], alpha: int) -> QColor:
    return QColor(rgb[0], rgb[1], rgb[2], max(0, min(255, alpha)))


def paint_scene(
    painter: QPainter,
    width: int,
    height: int,
    *,
    character: Character | str,
    visual: str,
    phase: float,
    glow: float,
    focus_progress: float,
    water_level: float | None,
    intention: str,
    sprite: QPixmap | None,
    palette: str,
    celebrate: float,
    clock_text: str | None,
    activity_label: str,
    activity: str = CHILL,
    mirror_typing: float = 0.0,
    mirror_clicking: float = 0.0,
    mirror: Mirror | None = None,
    history: list[tuple[str, float, bool]] | None = None,
    display_name: str | None = None,
    animate: bool = True,
) -> None:
    buddy = get_character(character if isinstance(character, str) else character.key)
    colors = PALETTES.get(palette, PALETTES["amber"])
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    cx = width / 2
    cy = float(BODY_Y)
    if visual == SCATTER:
        cx += math.sin(phase * 5.0) * 1.4

    breath = 1.0 + 0.016 * math.sin(phase * 0.65)
    if visual == SLEEPING:
        breath = 1.0 + 0.008 * math.sin(phase * 0.45)
    squash_x = 1.0 + 0.07 * mirror_clicking
    squash_y = 1.0 - 0.05 * mirror_clicking

    painter.save()
    painter.translate(cx, cy)
    painter.scale(breath * squash_x, breath * squash_y)
    painter.translate(-cx, -cy)

    _draw_shadow(painter, cx, cy + 46, visual)
    _draw_workstation(painter, cx, cy, colors, visual)
    _draw_halo(painter, cx, cy + 4, colors, visual, glow, celebrate)
    shift_x, shift_y, opacity = _idle_motion(buddy.body_shape, phase, visual, animate)
    painter.save()
    painter.translate(shift_x, shift_y)
    if opacity < 1.0:
        painter.setOpacity(opacity)
    if sprite is not None and not sprite.isNull():
        _draw_sprite(painter, cx, cy, sprite)
    else:
        if buddy.body_shape == "moth":
            _draw_flight_trail(painter, buddy, colors, cx, cy, phase, animate, visual)
        _draw_character(
            painter,
            buddy,
            colors,
            cx,
            cy + 2,
            visual,
            phase,
            glow,
            mirror_typing,
            _mood(visual, activity),
        )
        _draw_prop(painter, activity, buddy, colors, cx, cy + 32, phase)
        _draw_idle_extras(painter, buddy, colors, cx, cy, phase, animate, visual)
    painter.restore()
    if visual == FOCUS or focus_progress > 0:
        _draw_ring(painter, cx, cy, colors, focus_progress, celebrate)
    elif celebrate > 0:
        _draw_burst(painter, cx, cy, colors, celebrate)
    if water_level is not None:
        _draw_dew(painter, cx, cy, water_level, phase)
    painter.restore()

    if mirror is not None:
        mirror.draw(painter, cx, cy + 10, buddy.accent, colors["text"])

    _draw_caption(
        painter,
        width,
        height,
        colors,
        buddy,
        activity_label,
        intention,
        clock_text,
        history,
        display_name or buddy.name,
    )


# --------------------------------------------------------------------------
# Idle business
# --------------------------------------------------------------------------


# One short "something happens" window per slow cycle. The phase already moves
# at a different speed per mood, so this reads as an occasional fidget rather
# than a metronome.
def _action_envelope(
    phase: float, start: float = 0.70, span: float = 0.16, period: float = 42.0
) -> float:
    cycle = (max(0.0, phase) % period) / period
    if cycle < start or cycle > start + span:
        return 0.0
    return math.sin(math.pi * (cycle - start) / span)


def _idle_motion(shape: str, phase: float, visual: str, animate: bool) -> tuple[float, float, float]:
    """A little body travel for the flyers, hoppers, and drifters."""
    if not animate or visual != CALM:
        return 0.0, 0.0, 1.0
    envelope = _action_envelope(phase)
    if shape == "moth":
        return envelope * 19.0, -envelope * 9.0, 1.0 - 0.10 * envelope
    if shape == "frog":
        return 0.0, -envelope * 13.0, 1.0
    if shape == "ghost":
        return math.sin(phase * 0.9) * 2.2 + envelope * 6.0, 0.0, 1.0 - 0.18 * envelope
    if shape == "axolotl":
        return math.sin(phase * 1.6) * 2.2, 0.0, 1.0
    if shape == "cat":
        # A small pounce toward the yarn, then back to the loaf.
        return -envelope * 5.0, -envelope * 2.0, 1.0
    return 0.0, 0.0, 1.0


def _draw_flight_trail(
    painter: QPainter,
    buddy: Character,
    colors: dict[str, tuple[int, int, int]],
    cx: float,
    cy: float,
    phase: float,
    animate: bool,
    visual: str,
) -> None:
    if not animate or visual != CALM:
        return
    envelope = _action_envelope(phase)
    if envelope <= 0.04:
        return
    painter.setPen(Qt.PenStyle.NoPen)
    for index in range(3):
        alpha = int(70 * envelope * (1.0 - index / 3.2))
        painter.setBrush(_qc(colors["core"], alpha))
        painter.drawEllipse(
            QPointF(cx - 24 - index * 8, cy + 18 - index * 3 - envelope * 4),
            2.4 - index * 0.4,
            2.4 - index * 0.4,
        )


def _draw_idle_extras(
    painter: QPainter,
    buddy: Character,
    colors: dict[str, tuple[int, int, int]],
    cx: float,
    cy: float,
    phase: float,
    animate: bool,
    visual: str,
) -> None:
    """The cat's yarn, the swimmers' bubbles, a small ghostly shiver."""
    if not animate or visual != CALM:
        return
    shape = buddy.body_shape
    envelope = _action_envelope(phase)
    accent = buddy.accent
    if shape == "cat" and envelope > 0.05:
        # A yarn ball gets batted around, then rolls back out of reach.
        roll = envelope * 8.0 + math.sin(phase * 6.0) * envelope * 2.0
        bx, by = cx + 34 + roll, cy + 34
        painter.setPen(QPen(_qc(buddy.trim, 220), 1.2))
        painter.setBrush(_qc(accent, 245))
        painter.drawEllipse(QPointF(bx, by), 6.2, 6.2)
        painter.setPen(QPen(_qc(buddy.trim, 150), 0.8))
        painter.drawArc(QRectF(bx - 5, by - 4, 10, 8), 30 * 16, 120 * 16)
        painter.drawArc(QRectF(bx - 5, by - 1, 10, 6), 210 * 16, 110 * 16)
        string = QPainterPath()
        string.moveTo(bx + 5, by + 2)
        string.cubicTo(bx + 14, by + 8, cx + 12, cy + 26, cx + 4, cy + 24)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(_qc(accent, 150), 1.0))
        painter.drawPath(string)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_qc(buddy.body, 255))
        painter.drawEllipse(QRectF(bx - 13, by - 1, 9, 6))
    elif shape in ("axolotl", "frog") and envelope > 0.05:
        height = 10 + envelope * 10
        for index in range(3):
            alpha = int(150 * envelope * (1.0 - index / 3.0))
            painter.setPen(QPen(QColor(190, 230, 255, alpha), 0.8))
            painter.setBrush(QColor(170, 218, 255, int(alpha * 0.35)))
            painter.drawEllipse(
                QPointF(cx + 18 + index * 7, cy - 8 - height - index * 9),
                2.6 - index * 0.4,
                2.6 - index * 0.4,
            )
    elif shape == "ghost" and envelope > 0.05:
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(_qc(colors["ring"], int(80 * envelope)), 0.9))
        painter.drawEllipse(QPointF(cx, cy + 4), 33 + envelope * 5, 37 + envelope * 5)


# --------------------------------------------------------------------------
# Character bodies
# --------------------------------------------------------------------------


def _draw_character(
    painter: QPainter,
    buddy: Character,
    colors: dict[str, tuple[int, int, int]],
    cx: float,
    cy: float,
    visual: str,
    phase: float,
    glow: float,
    typing: float,
    mood: str = "happy",
) -> None:
    shape = buddy.body_shape
    if shape == "moth":
        _draw_moth(painter, colors, cx, cy, visual, phase, glow, mood)
    elif shape == "cat":
        _draw_cat(painter, buddy, cx, cy, visual, phase, typing, mood)
    elif shape == "frog":
        _draw_frog(painter, buddy, cx, cy, visual, phase, typing, mood)
    elif shape == "ghost":
        _draw_ghost(painter, buddy, cx, cy, visual, phase, typing, mood)
    elif shape == "axolotl":
        _draw_axolotl(painter, buddy, cx, cy, visual, phase, typing, mood)
    else:
        _draw_moth(painter, colors, cx, cy, visual, phase, glow, mood)


def _blink(phase: float, rate: float = 0.38) -> bool:
    return math.sin(phase * rate) > 0.945


def _draw_sleep_marks(
    painter: QPainter,
    x: float,
    y: float,
    accent: tuple[int, int, int],
    phase: float,
) -> None:
    font = QFont("Segoe UI", 8)
    font.setWeight(QFont.Weight.DemiBold)
    painter.setFont(font)
    for index in range(2):
        drift = (phase * 0.5 + index * 1.7) % 3.0
        alpha = int(150 * max(0.0, 1.0 - drift / 3.0))
        painter.setPen(QColor(accent[0], accent[1], accent[2], alpha))
        painter.drawText(QPointF(x + 6 + index * 4 + drift * 1.2, y - index * 7 - drift * 2.4), "z")


def _draw_workstation(
    painter: QPainter,
    cx: float,
    cy: float,
    colors: dict[str, tuple[int, int, int]],
    visual: str,
) -> None:
    """A tiny desk so the perch feels like a real workstation."""
    painter.save()
    desk_y = cy + 58
    # Desk surface.
    painter.setPen(QPen(_qc(colors["plate"], 80), 1.0))
    painter.setBrush(_qc((92, 62, 40), 210))
    painter.drawRoundedRect(QRectF(cx - 78, desk_y, 156, 12), 4, 4)
    # Legs.
    painter.setBrush(_qc((70, 48, 32), 230))
    for x in (-62, 62):
        painter.drawRoundedRect(QRectF(cx + x - 3, desk_y + 10, 6, 18), 2, 2)
    # Monitor.
    painter.setBrush(_qc((34, 34, 46), 235))
    painter.setPen(QPen(_qc(colors["edge"], 120), 1.0))
    painter.drawRoundedRect(QRectF(cx - 26, desk_y - 34, 52, 30), 4, 4)
    painter.setBrush(_qc(colors["core"], 95 if visual != SLEEPING else 45))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(QRectF(cx - 22, desk_y - 30, 44, 22), 3, 3)
    # Stand and keyboard.
    painter.setBrush(_qc((52, 42, 34), 230))
    painter.drawRoundedRect(QRectF(cx - 3, desk_y - 4, 6, 8), 1, 1)
    painter.drawRoundedRect(QRectF(cx - 34, desk_y - 2, 68, 7), 2, 2)
    # A tiny lamp, because it is a desk companion.
    painter.setPen(QPen(_qc(colors["edge"], 180), 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(QPointF(cx + 46, desk_y), QPointF(cx + 52, desk_y - 16))
    painter.setBrush(_qc(colors["core"], 170))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(QPointF(cx + 52, desk_y - 18), 3.2, 3.2)
    painter.restore()


def _draw_shadow(painter: QPainter, cx: float, y: float, visual: str) -> None:
    alpha = 26 if visual == SLEEPING else 46
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(10, 6, 18, alpha))
    painter.drawEllipse(QPointF(cx, y), 40, 8)


def _draw_halo(
    painter: QPainter,
    cx: float,
    cy: float,
    colors: dict[str, tuple[int, int, int]],
    visual: str,
    glow: float,
    celebrate: float,
) -> None:
    strength = glow + 0.35 * celebrate
    radius = 62 if visual != SLEEPING else 42
    halo = QRadialGradient(cx, cy, radius)
    halo.setColorAt(0.0, _qc(colors["edge"], int(80 + 100 * strength)))
    halo.setColorAt(0.45, _qc(colors["edge"], int(24 + 36 * strength)))
    halo.setColorAt(1.0, _qc(colors["edge"], 0))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(halo)
    painter.drawEllipse(QPointF(cx, cy), radius, radius * 0.92)


def _wing_path() -> QPainterPath:
    path = QPainterPath()
    path.moveTo(0, 6)
    path.cubicTo(26, -18, 62, -58, 96, -28)
    path.cubicTo(118, -4, 104, 36, 70, 48)
    path.cubicTo(40, 44, 16, 28, 0, 6)
    path.closeSubpath()
    return path


def _flap(visual: str, phase: float) -> float:
    if visual == SLEEPING:
        return 46 + math.sin(phase) * 2.2
    if visual == SCATTER:
        return 14 + math.sin(phase * 2.15) * 16 + math.sin(phase * 3.4) * 4
    amplitude = {CALM: 13, WORKING: 20, FOCUS: 10}.get(visual, 13)
    rest = {CALM: 18, WORKING: 12, FOCUS: 16}.get(visual, 16)
    return rest + math.sin(phase) * amplitude


def _draw_moth(
    painter: QPainter,
    colors: dict[str, tuple[int, int, int]],
    cx: float,
    cy: float,
    visual: str,
    phase: float,
    glow: float,
    mood: str = "happy",
) -> None:
    wing_rgb = colors["wing"] if visual in (WORKING, FOCUS, SCATTER) else colors["wing_calm"]
    if visual == SLEEPING:
        wing_rgb = colors["wing_calm"]
    membrane_alpha = 70 if visual == SLEEPING else 118
    angle = _flap(visual, phase)
    path = _wing_path()
    painter.save()
    painter.translate(cx, cy + 2)
    painter.scale(0.66, 0.66)
    painter.translate(-cx, -cy)
    for sign in (-1, 1):
        painter.save()
        painter.translate(cx, cy - 6)
        painter.rotate(sign * angle)
        painter.scale(sign, 1)
        painter.setPen(QPen(_qc(colors["edge"], 175), 1.3))
        painter.setBrush(_qc(wing_rgb, membrane_alpha))
        painter.drawPath(path)
        vein = QPainterPath()
        vein.moveTo(8, 4)
        vein.cubicTo(36, -8, 70, -16, 92, -6)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(_qc(colors["vein"], 115), 1.15))
        painter.drawPath(vein)
        painter.restore()
    painter.restore()

    # The head and lantern keep their own, larger scale so the face reads at
    # this small size instead of disappearing between the wings.
    painter.save()
    painter.translate(cx, cy + 4)
    painter.scale(0.82, 0.82)
    painter.translate(-cx, -cy)
    core = colors["core"]
    edge = colors["edge"]
    if visual == SCATTER:
        core = (214, 252, 255)
        edge = (90, 198, 214)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(_qc(colors["body"], 235 if visual != SLEEPING else 200))
    painter.drawEllipse(QRectF(cx - 15, cy - 30, 30, 62))
    lantern = QRadialGradient(cx, cy + 10, 26)
    light = 0.15 + 0.85 * max(0.12, min(1.0, glow))
    lantern.setColorAt(0.0, _qc(core, int(230 * light)))
    lantern.setColorAt(0.55, _qc(edge, int(150 * light)))
    lantern.setColorAt(1.0, _qc(edge, 0))
    painter.setBrush(lantern)
    painter.drawEllipse(QRectF(cx - 17, cy - 3, 34, 37))

    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(_qc(colors["vein"], 150), 1.15, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(QPointF(cx - 5, cy - 26), QPointF(cx - 14, cy - 48))
    painter.drawLine(QPointF(cx + 5, cy - 26), QPointF(cx + 14, cy - 48))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(_qc(core, 220))
    painter.drawEllipse(QPointF(cx - 14, cy - 48), 2.3, 2.3)
    painter.drawEllipse(QPointF(cx + 14, cy - 48), 2.3, 2.3)

    if visual == SLEEPING or _blink(phase):
        painter.setPen(QPen(_qc(colors["text"], 190), 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawArc(QRectF(cx - 9, cy - 20, 6, 5), 200 * 16, 140 * 16)
        painter.drawArc(QRectF(cx + 3, cy - 20, 6, 5), 200 * 16, 140 * 16)
        if visual == SLEEPING:
            _draw_sleep_marks(painter, cx + 20, cy - 24, colors["ring"], phase)
    else:
        painter.setBrush(QColor(12, 8, 18, 230))
        painter.drawEllipse(QRectF(cx - 8, cy - 18, 4.2, 5.0))
        painter.drawEllipse(QRectF(cx + 3.6, cy - 18, 4.2, 5.0))
        painter.setBrush(_qc(core, 220))
        painter.drawEllipse(QPointF(cx - 6.2, cy - 16.6), 0.9, 0.9)
        painter.drawEllipse(QPointF(cx + 5.4, cy - 16.6), 0.9, 0.9)
    if mood != "sleep":
        _mood_mouth(painter, cx, cy - 12, mood, colors["text"], colors["core"], 10.0)
    painter.restore()


def _draw_prop(
    painter: QPainter,
    activity: str,
    buddy: Character,
    colors: dict[str, tuple[int, int, int]],
    cx: float,
    cy: float,
    phase: float,
) -> None:
    """The thing the buddy is doing with you: book, laptop, or gamepad."""
    if activity not in (STUDY, WORK, GAMING):
        return
    bob = math.sin(phase * 3.2) * 0.6
    painter.save()
    painter.translate(cx, cy + bob)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    if activity == STUDY:
        painter.rotate(-3)
        painter.setPen(QPen(_qc(buddy.trim, 220), 1.3))
        painter.setBrush(_qc(buddy.trim, 245))
        painter.drawRoundedRect(QRectF(-20, -9, 40, 18), 2.5, 2.5)
        painter.setBrush(QColor(250, 246, 235, 250))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(-18, -7, 16.5, 14), 1.6, 1.6)
        painter.drawRoundedRect(QRectF(1.5, -7, 16.5, 14), 1.6, 1.6)
        painter.setPen(QPen(_qc(colors["text"], 110), 0.8))
        for row in range(3):
            y = -3.4 + row * 3.4
            painter.drawLine(QPointF(-15.5, y), QPointF(-4.0, y))
            painter.drawLine(QPointF(4.0, y), QPointF(15.5, y))
    elif activity == WORK:
        painter.setPen(QPen(_qc(buddy.trim, 230), 1.1))
        painter.setBrush(_qc(buddy.trim, 245))
        screen = QPainterPath()
        screen.moveTo(-16, -2)
        screen.lineTo(-13, -17)
        screen.lineTo(13, -17)
        screen.lineTo(16, -2)
        screen.closeSubpath()
        painter.drawPath(screen)
        painter.setBrush(QColor(18, 14, 26, 245))
        painter.drawPath(screen)
        painter.setPen(QPen(_qc(buddy.accent, 235), 1.1))
        painter.drawLine(QPointF(-9, -12.5), QPointF(-6, -10.0))
        painter.drawLine(QPointF(-9, -7.5), QPointF(-6, -10.0))
        painter.drawLine(QPointF(-1, -10.0), QPointF(8, -10.0))
        painter.drawLine(QPointF(0, -6.6), QPointF(6, -6.6))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_qc(buddy.trim, 245))
        painter.drawRoundedRect(QRectF(-20, -2, 40, 5), 1.8, 1.8)
        painter.setPen(QPen(_qc(buddy.accent, 140), 0.7))
        for col in range(5):
            painter.drawLine(QPointF(-15 + col * 7, 0.4), QPointF(-12 + col * 7, 0.4))
    else:
        painter.setPen(QPen(_qc(buddy.trim, 235), 1.2))
        painter.setBrush(_qc(buddy.trim, 240))
        painter.drawRoundedRect(QRectF(-17, -6, 34, 13), 6, 6)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_qc(buddy.accent, 245))
        painter.drawRoundedRect(QRectF(-12, -3.5, 4, 8), 1.2, 1.2)
        painter.drawRoundedRect(QRectF(-14, -1.5, 8, 4), 1.2, 1.2)
        painter.setBrush(QColor(255, 255, 255, 235))
        painter.drawEllipse(QPointF(10, -2.0), 1.8, 1.8)
        painter.drawEllipse(QPointF(6.5, 1.5), 1.8, 1.8)
    painter.restore()


def _draw_cat(
    painter: QPainter,
    buddy: Character,
    cx: float,
    cy: float,
    visual: str,
    phase: float,
    typing: float,
    mood: str = "happy",
) -> None:
    bob = math.sin(phase * 1.5) * 1.2 + typing * math.sin(phase * 9) * 1.4
    if visual == SLEEPING:
        bob = math.sin(phase * 0.4) * 0.8
    body = buddy.body
    trim = buddy.trim
    accent = buddy.accent

    # Tail, behind everything.
    swing = math.sin(phase * (4.0 if visual == SCATTER else 1.1)) * (10 if visual != SLEEPING else 3)
    tail = QPainterPath()
    tail.moveTo(cx + 28, cy + 28 + bob)
    tail.cubicTo(cx + 58, cy + 34, cx + 56 + swing, cy + 2, cx + 42 + swing, cy - 8)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(_qc(trim, 220), 5.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawPath(tail)

    painter.setPen(QPen(_qc(trim, 235), 1.8))
    painter.setBrush(_qc(body, 255))
    # Loaf and head.
    painter.drawEllipse(QRectF(cx - 33, cy - 4 + bob, 66, 40))
    painter.drawEllipse(QRectF(cx - 25, cy - 40 + bob, 50, 44))

    # Ears.
    for sign in (-1, 1):
        ear = QPainterPath()
        ear.moveTo(cx + sign * 23, cy - 30 + bob)
        ear.lineTo(cx + sign * 25, cy - 54 + bob)
        ear.lineTo(cx + sign * 7, cy - 39 + bob)
        ear.closeSubpath()
        painter.setBrush(_qc(body, 255))
        painter.drawPath(ear)
        inner = QPainterPath()
        inner.moveTo(cx + sign * 20, cy - 33 + bob)
        inner.lineTo(cx + sign * 21, cy - 47 + bob)
        inner.lineTo(cx + sign * 12, cy - 39 + bob)
        inner.closeSubpath()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_qc(accent, 210))
        painter.drawPath(inner)
        painter.setPen(QPen(_qc(trim, 235), 1.8))

    # Paws, tapping in alternation while you type.
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(_qc(body, 255))
    for sign in (-1, 1):
        lift = 0.0
        if typing > 0.05 and visual != SLEEPING:
            lift = max(0.0, math.sin(phase * 9 + (0 if sign < 0 else math.pi))) * 3.5 * typing
        painter.drawEllipse(QRectF(cx + sign * 17 - 7, cy + 26 + bob - lift, 14, 9))

    # Face.
    painter.setPen(QPen(_qc(trim, 240), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    if visual == SLEEPING or _blink(phase):
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(QRectF(cx - 16, cy - 26 + bob, 10, 6), 200 * 16, 140 * 16)
        painter.drawArc(QRectF(cx + 6, cy - 26 + bob, 10, 6), 200 * 16, 140 * 16)
    else:
        eye_h = 6.0 if visual != SCATTER else 7.0
        painter.setBrush(QColor(46, 32, 40, 245))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(cx - 15, cy - 28 + bob, 5.5, eye_h))
        painter.drawEllipse(QRectF(cx + 9.5, cy - 28 + bob, 5.5, eye_h))
        painter.setBrush(QColor(255, 255, 255, 220))
        painter.drawEllipse(QPointF(cx - 13.4, cy - 26.6 + bob), 1.1, 1.1)
        painter.drawEllipse(QPointF(cx + 11.1, cy - 26.6 + bob), 1.1, 1.1)

    # Nose and a tiny omega mouth.
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(_qc(accent, 255))
    painter.drawEllipse(QPointF(cx, cy - 17 + bob), 2.0, 1.5)
    _mood_mouth(painter, cx, cy - 16 + bob, mood, trim, accent, 7.2)

    # Whiskers.
    painter.setPen(QPen(_qc(trim, 110), 0.9))
    for sign in (-1, 1):
        for offset in (-2.0, 3.0):
            painter.drawLine(
                QPointF(cx + sign * 11, cy - 14 + offset + bob),
                QPointF(cx + sign * 30, cy - 16 + offset * 1.3 + bob),
            )

    if visual == SLEEPING:
        _draw_sleep_marks(painter, cx + 18, cy - 34, accent, phase)


def _draw_frog(
    painter: QPainter,
    buddy: Character,
    cx: float,
    cy: float,
    visual: str,
    phase: float,
    typing: float,
    mood: str = "happy",
) -> None:
    bob = math.sin(phase * 1.7) * 1.1 + typing * math.sin(phase * 8) * 1.2
    if visual == SLEEPING:
        bob = math.sin(phase * 0.4) * 0.7
    body = buddy.body
    trim = buddy.trim
    accent = buddy.accent

    # Back feet.
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(_qc(body, 255))
    for sign in (-1, 1):
        painter.drawEllipse(QRectF(cx + sign * 28 - 10, cy + 25 + bob, 20, 10))

    painter.setPen(QPen(_qc(trim, 225), 1.7))
    painter.setBrush(_qc(body, 255))
    painter.drawEllipse(QRectF(cx - 35, cy - 4 + bob, 70, 40))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(_qc(accent, 150))
    painter.drawEllipse(QRectF(cx - 21, cy + 3 + bob, 42, 27))

    # Eye bumps.
    painter.setBrush(_qc(body, 255))
    painter.setPen(QPen(_qc(trim, 225), 1.6))
    for sign in (-1, 1):
        painter.drawEllipse(QRectF(cx + sign * 16 - 13, cy - 38 + bob, 26, 26))

    # Front toes.
    painter.setPen(QPen(_qc(trim, 190), 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    for sign in (-1, 1):
        for toe in (-1, 0, 1):
            painter.drawLine(
                QPointF(cx + sign * 18 + toe * 3.5, cy + 30 + bob),
                QPointF(cx + sign * 18 + toe * 5.0, cy + 35 + bob),
            )

    # Eyes.
    blink = visual == SLEEPING or _blink(phase, 0.33)
    for sign in (-1, 1):
        ex = cx + sign * 16
        if blink:
            painter.setPen(QPen(_qc(trim, 235), 1.7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawArc(QRectF(ex - 7, cy - 31 + bob, 14, 7), 200 * 16, 140 * 16)
            continue
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(250, 252, 246, 250))
        painter.drawEllipse(QRectF(ex - 8, cy - 34 + bob, 16, 16))
        painter.setBrush(QColor(34, 48, 38, 250))
        shift = 0.0
        if visual == SCATTER:
            shift = math.sin(phase * 6.0) * 2.4
        painter.drawEllipse(QRectF(ex - 3.6 + shift, cy - 29 + bob, 7.2, 7.2))
        painter.setBrush(QColor(255, 255, 255, 235))
        painter.drawEllipse(QPointF(ex - 1.6 + shift, cy - 27 + bob), 1.5, 1.5)

    # Mouth.
    width = 18 if visual != SCATTER else 22
    _mood_mouth(painter, cx, cy - 10 + bob, mood, trim, accent, float(width))

    # Cheek dots.
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(_qc(buddy.accent, 170))
    painter.drawEllipse(QRectF(cx - 29, cy - 14 + bob, 7, 4))
    painter.drawEllipse(QRectF(cx + 22, cy - 14 + bob, 7, 4))

    if visual == SLEEPING:
        _draw_sleep_marks(painter, cx + 22, cy - 30, accent, phase)


def _draw_ghost(
    painter: QPainter,
    buddy: Character,
    cx: float,
    cy: float,
    visual: str,
    phase: float,
    typing: float,
    mood: str = "happy",
) -> None:
    bob = math.sin(phase * 1.3) * 2.2 + typing * math.sin(phase * 7) * 1.0
    body = buddy.body
    trim = buddy.trim
    accent = buddy.accent
    top = cy - 38 + bob
    bottom = cy + 28 + bob

    path = QPainterPath()
    path.moveTo(cx - 26, bottom)
    path.lineTo(cx - 26, cy - 10 + bob)
    path.cubicTo(cx - 26, top - 8, cx + 26, top - 8, cx + 26, cy - 10 + bob)
    path.lineTo(cx + 26, bottom)
    scallops = 4
    step = 52.0 / scallops
    for index in range(scallops):
        x0 = cx + 26 - index * step
        path.quadTo(x0 - step / 2, bottom - 7, x0 - step, bottom)
    path.closeSubpath()

    painter.setPen(QPen(_qc(accent, 210), 1.5))
    painter.setBrush(_qc(body, 228))
    painter.drawPath(path)

    # Little arms.
    painter.setPen(QPen(_qc(body, 235), 5.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(QPointF(cx - 25, cy + 2 + bob), QPointF(cx - 34, cy + 8 + bob))
    painter.drawLine(QPointF(cx + 25, cy + 2 + bob), QPointF(cx + 34, cy + 8 + bob))

    # Face.
    painter.setPen(Qt.PenStyle.NoPen)
    if visual == SLEEPING or _blink(phase, 0.3):
        painter.setPen(QPen(_qc(trim, 235), 1.7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(QRectF(cx - 15, cy - 24 + bob, 10, 6), 200 * 16, 140 * 16)
        painter.drawArc(QRectF(cx + 5, cy - 24 + bob, 10, 6), 200 * 16, 140 * 16)
    else:
        painter.setBrush(QColor(48, 38, 68, 245))
        eye_w = 6.0 if visual != SCATTER else 7.0
        painter.drawEllipse(QRectF(cx - 13, cy - 26 + bob, eye_w, 8.0))
        painter.drawEllipse(QRectF(cx + 7, cy - 26 + bob, eye_w, 8.0))
        painter.setBrush(QColor(255, 255, 255, 235))
        painter.drawEllipse(QPointF(cx - 11 + 1, cy - 24 + bob), 1.2, 1.2)
        painter.drawEllipse(QPointF(cx + 9 + 1, cy - 24 + bob), 1.2, 1.2)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        mouth_w = 10 if visual != SCATTER else 13
        _mood_mouth(painter, cx, cy - 12 + bob, mood, trim, accent, float(mouth_w))

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(_qc(buddy.accent, 120))
    painter.drawEllipse(QRectF(cx - 21, cy - 16 + bob, 7, 4))
    painter.drawEllipse(QRectF(cx + 14, cy - 16 + bob, 7, 4))

    if visual == SLEEPING:
        _draw_sleep_marks(painter, cx + 18, cy - 34, accent, phase)


def _draw_axolotl(
    painter: QPainter,
    buddy: Character,
    cx: float,
    cy: float,
    visual: str,
    phase: float,
    typing: float,
    mood: str = "happy",
) -> None:
    bob = math.sin(phase * 1.5) * 1.2 + typing * math.sin(phase * 9) * 1.3
    if visual == SLEEPING:
        bob = math.sin(phase * 0.42) * 0.7
    body = buddy.body
    trim = buddy.trim
    accent = buddy.accent

    # Tail.
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(_qc(body, 240), 7.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    tail = QPainterPath()
    tail.moveTo(cx - 26, cy + 28 + bob)
    tail.cubicTo(cx - 48, cy + 26, cx - 52, cy + 6, cx - 40, cy + 2)
    painter.drawPath(tail)

    # Gills: three fronds each side.
    for sign in (-1, 1):
        for index, angle in enumerate((-28, -4, 20)):
            length = 13 + index * 2
            base = QPointF(cx + sign * 24, cy - 22 + bob + index * 5)
            tip = QPointF(
                base.x() + sign * (length * math.cos(math.radians(angle))),
                base.y() + length * math.sin(math.radians(angle)),
            )
            painter.setPen(QPen(_qc(buddy.accent, 245), 3.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(base, tip)
            painter.setPen(QPen(_qc(trim, 150), 1.1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(tip, QPointF(tip.x() + sign * 3, tip.y() - 3))

    painter.setPen(QPen(_qc(trim, 220), 1.7))
    painter.setBrush(_qc(body, 255))
    painter.drawEllipse(QRectF(cx - 31, cy - 8 + bob, 62, 42))
    painter.drawEllipse(QRectF(cx - 27, cy - 38 + bob, 54, 46))

    # Belly.
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(_qc(accent, 135))
    painter.drawEllipse(QRectF(cx - 16, cy + 4 + bob, 32, 24))

    # Feet.
    painter.setBrush(_qc(body, 255))
    for sign in (-1, 1):
        painter.drawEllipse(QRectF(cx + sign * 20 - 7, cy + 28 + bob, 14, 8))

    # Face.
    blink = visual == SLEEPING or _blink(phase, 0.36)
    for sign in (-1, 1):
        ex = cx + sign * 12
        if blink:
            painter.setPen(QPen(_qc(trim, 235), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawArc(QRectF(ex - 6, cy - 24 + bob, 12, 6), 200 * 16, 140 * 16)
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(52, 34, 48, 245))
            painter.drawEllipse(QRectF(ex - 3.4, cy - 27 + bob, 6.8, 7.6))
            painter.setBrush(QColor(255, 255, 255, 230))
            painter.drawEllipse(QPointF(ex - 1.4, cy - 25 + bob), 1.2, 1.2)
    # Smile.
    _mood_mouth(painter, cx, cy - 12 + bob, mood, trim, accent, 14.0)

    # Blush.
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(_qc(buddy.accent, 210))
    painter.drawEllipse(QRectF(cx - 23, cy - 14 + bob, 7, 4))
    painter.drawEllipse(QRectF(cx + 16, cy - 14 + bob, 7, 4))

    if visual == SLEEPING:
        _draw_sleep_marks(painter, cx + 20, cy - 32, trim, phase)


# --------------------------------------------------------------------------
# Scene furniture
# --------------------------------------------------------------------------


def _draw_sprite(painter: QPainter, cx: float, cy: float, sprite: QPixmap) -> None:
    max_h = 112.0
    max_w = 120.0
    # Fit in both directions. A small hand-drawn buddy should still be visible
    # instead of arriving as a twenty-pixel dot.
    scale = min(max_h / max(1, sprite.height()), max_w / max(1, sprite.width()))
    width = sprite.width() * scale
    height = sprite.height() * scale
    painter.drawPixmap(
        QRectF(cx - width / 2, cy - height / 2 + 2, width, height),
        sprite,
        QRectF(0, 0, sprite.width(), sprite.height()),
    )


def _draw_ring(
    painter: QPainter,
    cx: float,
    cy: float,
    colors: dict[str, tuple[int, int, int]],
    progress: float,
    celebrate: float,
) -> None:
    radius = 68
    rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(_qc(colors["ring"], 50), 2.6))
    painter.drawEllipse(rect)
    span = int(-max(0.02, progress) * 360 * 16)
    painter.setPen(QPen(_qc(colors["ring"], 230), 2.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawArc(rect, 90 * 16, span)
    if celebrate > 0:
        _draw_burst(painter, cx, cy, colors, celebrate)


def _draw_burst(
    painter: QPainter,
    cx: float,
    cy: float,
    colors: dict[str, tuple[int, int, int]],
    celebrate: float,
) -> None:
    radius = 48 + (1.0 - celebrate) * 32
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(_qc(colors["ring"], int(200 * celebrate)), 1.8))
    painter.drawEllipse(QPointF(cx, cy), radius, radius * 0.92)


def _draw_dew(painter: QPainter, cx: float, cy: float, level: float, phase: float) -> None:
    pulse = 0.5 + 0.5 * math.sin(phase * 1.4)
    height = 10 + 12 * level
    alpha = int(130 + 90 * level * (0.65 + 0.35 * pulse))
    drop = QPainterPath()
    top_y = cy + 44 - height
    drop.moveTo(cx + 42, top_y)
    drop.quadTo(cx + 54, top_y + height * 0.55, cx + 42, top_y + height)
    drop.quadTo(cx + 30, top_y + height * 0.55, cx + 42, top_y)
    painter.setPen(QPen(QColor(210, 236, 255, alpha), 0.9))
    painter.setBrush(QColor(150, 206, 255, int(alpha * 0.7)))
    painter.drawPath(drop)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(255, 255, 255, 180))
    painter.drawEllipse(QPointF(cx + 38, top_y + height * 0.38), 1.3, 1.8)


def _draw_caption(
    painter: QPainter,
    width: int,
    height: int,
    colors: dict[str, tuple[int, int, int]],
    buddy: Character,
    activity_label: str,
    intention: str,
    clock_text: str | None,
    history: list[tuple[str, float, bool]] | None,
    display_name: str,
) -> None:
    plate_h = 58 if intention else 44
    plate = QRectF(PLATE_MARGIN, height - plate_h - 12, width - PLATE_MARGIN * 2, plate_h)
    painter.setPen(QPen(_qc(buddy.accent, 55), 1.0))
    painter.setBrush(_qc(colors["plate"], 140))
    painter.drawRoundedRect(plate, 13, 13)

    painter.setPen(_qc(colors["text"], 240))
    title_font = QFont("Segoe UI", 11)
    title_font.setWeight(QFont.Weight.DemiBold)
    painter.setFont(title_font)
    painter.drawText(
        QRectF(plate.x(), plate.y() + 5, plate.width(), 18),
        Qt.AlignmentFlag.AlignHCenter,
        display_name,
    )

    status = clock_text or activity_label
    sub_font = QFont("Segoe UI", 8)
    painter.setFont(sub_font)
    painter.setPen(_qc(buddy.accent, 245))
    painter.drawText(
        QRectF(plate.x(), plate.y() + 23, plate.width(), 15),
        Qt.AlignmentFlag.AlignHCenter,
        status,
    )
    if intention:
        line_font = QFont("Segoe UI", 7)
        line_font.setItalic(True)
        painter.setFont(line_font)
        painter.setPen(_qc(colors["text"], 190))
        shown = QFontMetrics(line_font).elidedText(
            intention, Qt.TextElideMode.ElideRight, int(plate.width()) - 16
        )
        painter.drawText(
            QRectF(plate.x() + 6, plate.y() + 39, plate.width() - 12, 14),
            Qt.AlignmentFlag.AlignHCenter,
            shown,
        )
    if history:
        _draw_sparkline(painter, plate, colors, history)


def _draw_sparkline(
    painter: QPainter,
    plate: QRectF,
    colors: dict[str, tuple[int, int, int]],
    history: list[tuple[str, float, bool]],
) -> None:
    """Seven tiny bars in the plate's top-right corner: six days and today."""
    values = [seconds for _day, seconds, _today in history]
    if not values or max(values) <= 0:
        return
    bar_w, gap, height = 2.5, 2.0, 9.0
    total = len(history) * bar_w + (len(history) - 1) * gap
    x0 = plate.right() - 9 - total
    base = plate.y() + 6 + height
    peak = max(values)
    painter.setPen(Qt.PenStyle.NoPen)
    for index, (_day, seconds, is_today) in enumerate(history):
        share = seconds / peak if peak > 0 else 0.0
        bar_h = 2.2 + (height - 2.2) * share
        alpha = 235 if is_today else 90
        painter.setBrush(_qc(colors["ring"], alpha))
        painter.drawRoundedRect(
            QRectF(x0 + index * (bar_w + gap), base - bar_h, bar_w, bar_h),
            1.1,
            1.1,
        )


def build_tray_icon(palette: str, character: Character | str = "moth") -> QIcon:
    """A small buddy, scaled down from the same body the window paints."""
    buddy = get_character(character if isinstance(character, str) else character.key)
    pix = QPixmap(64, 64)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    colors = PALETTES.get(palette, PALETTES["amber"])
    painter.translate(32, 36)
    painter.scale(0.44, 0.44)
    painter.translate(-CANVAS_W / 2, -BODY_Y)
    _draw_halo(painter, CANVAS_W / 2, BODY_Y + 4, colors, CALM, 0.85, 0)
    _draw_character(painter, buddy, colors, CANVAS_W / 2, BODY_Y + 2, CALM, 0.7, 0.85, 0.0)
    painter.end()
    return QIcon(pix)
