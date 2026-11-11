"""The frameless perch: drag, paint, rituals, and the right-click menu.

The window never takes keyboard focus, so dragging it does not knock you out
of whatever you were typing. On Windows, empty pixels answer hit-tests with
HTTRANSPARENT and the click lands on the desktop instead of a hidden rectangle.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging
import math
import random
import sys
import time
from functools import partial
from html import escape as html_escape

from PyQt6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, QTimer
from PyQt6.QtGui import (
    QAction,
    QActionGroup,
    QColor,
    QCursor,
    QFont,
    QGuiApplication,
    QPainter,
    QPen,
    QPolygonF,
)
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

import autostart
import focus_history
import glimmer
from activity import (
    ACTIVITY_LABELS,
    AWAY,
    AWAY_AFTER_SECONDS,
    CHILL,
    GAMING,
    STUDY,
    WORK,
    ActivityJudge,
)
from characters import CHARACTER_ORDER, CHARACTERS, get as get_character, next_key
from chatter import Chatter
from chime import play as play_chime
from converse import MAX_QUESTION, reply as converse_reply
from custom import custom_dirs, install_custom_buddies
from paths import asset_dirs
from safety import clean_text
from painter import CANVAS_H, CANVAS_W, BODY_Y, build_tray_icon, paint_scene
from reactions import Mirror
import rewards
import sounds
from rituals import RitualClock
from settings_store import Settings, load_settings
from sprites import SpriteLibrary
from states import CALM, FOCUS, SCATTER, SLEEPING, WORKING
from theme import COAT_LABELS, COAT_ORDER, PALETTE_LABELS, PALETTE_ORDER
from ui_engine_theme import shell_palette, pop_accent
from tracker import BURST_WINDOW_SECONDS, WIDE_WINDOW_SECONDS, InputTracker, Pulse
from tricks import DASH, PEEK, Trick, sample as sample_trick, tricks_for



































































































































































































































































































































































































































































































































































log = logging.getLogger("lumen")

MENU_QSS = """
QMenu {
    background-color: rgba(22, 16, 34, 235);
    color: #f6f1e8;
    border: 1px solid rgba(255, 214, 160, 80);
    border-radius: 10px;
    padding: 6px;
}
QMenu::item {
    padding: 6px 18px;
    border-radius: 6px;
    background: transparent;
}
QMenu::item:selected {
    background-color: rgba(255, 176, 90, 55);
}
QMenu::item:disabled {
    color: rgba(246, 241, 232, 150);
}
QMenu::separator {
    height: 1px;
    background: rgba(255, 255, 255, 28);
    margin: 5px 10px;
}
"""

WM_NCHITTEST = 0x0084
HTTRANSPARENT = -1


def _window_flags(tool: bool) -> Qt.WindowType:
    flags = (
        Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.WindowStaysOnTopHint
        | Qt.WindowType.NoDropShadowWindowHint
        | Qt.WindowType.WindowDoesNotAcceptFocus
    )
    if tool:
        flags |= Qt.WindowType.Tool
    return flags


class LanternNote(QWidget):
    """A speech bubble beside the buddy. It never takes focus or quits the app."""

    def __init__(self) -> None:
        super().__init__(None)
        self.setWindowFlags(_window_flags(tool=True))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setWindowFlag(Qt.WindowType.WindowTransparentForInput, True)
        self._text = ""
        self._name = ""
        self._tail_side = "left"
        self._accent = QColor(255, 186, 122)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)
        self.setFixedSize(210, 60)

    def present(
        self,
        name: str,
        text: str,
        accent: tuple[int, int, int],
        anchor: QPoint,
    ) -> None:
        self._name = name
        self._text = text
        self._accent = QColor(*accent)
        screen = QApplication.screenAt(anchor) or QApplication.primaryScreen()
        geo = screen.availableGeometry() if screen is not None else QRect(0, 0, 1280, 720)
        # Keep the toast beside the buddy instead of over its face. It is
        # deliberately small, short-lived, and click-through so it cannot
        # steal input from the work underneath it.
        half_buddy = CANVAS_W // 2
        right_x = anchor.x() + half_buddy + 10
        left_x = anchor.x() - half_buddy - self.width() - 10
        x = right_x if right_x + self.width() <= geo.right() - 8 else left_x
        x = min(max(geo.left() + 8, x), geo.right() - self.width() - 8)
        self._tail_side = "left" if x >= anchor.x() else "right"
        y = anchor.y() - self.height() // 2
        y = min(max(geo.top() + 8, y), geo.bottom() - self.height() - 8)
        self.move(x, y)
        self.show()
        self.raise_()
        self.update()
        self._timer.start(3600)

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        inset = 8 if self._tail_side == "left" else 1
        far_inset = 8 if self._tail_side == "right" else 1
        bubble = QRectF(inset, 1, self.width() - inset - far_inset, self.height() - 2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(22, 16, 34, 232))
        painter.drawRoundedRect(bubble, 13, 13)
        painter.setPen(QPen(QColor(self._accent.red(), self._accent.green(), self._accent.blue(), 90), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(bubble, 13, 13)

        tail_y = self.height() / 2
        if self._tail_side == "left":
            tail = QPolygonF([QPointF(bubble.left() + 1, tail_y - 7),
                              QPointF(bubble.left() + 1, tail_y + 7),
                              QPointF(1, tail_y)])
        else:
            tail = QPolygonF([QPointF(bubble.right() - 1, tail_y - 7),
                              QPointF(bubble.right() - 1, tail_y + 7),
                              QPointF(self.width() - 1, tail_y)])
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(22, 16, 34, 232))
        painter.drawPolygon(tail)

        name_font = QFont("Segoe UI", 7)
        name_font.setWeight(QFont.Weight.DemiBold)
        name_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.8)
        painter.setFont(name_font)
        painter.setPen(self._accent)
        painter.drawText(
            QRectF(12, 4, self.width() - 24, 13),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self._name.upper(),
        )

        painter.setPen(QColor(255, 244, 232))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(
            QRectF(12, 18, self.width() - 24, self.height() - 25),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
            self._text,
        )
        painter.end()


class VigilVeil(QWidget):
    """A dim sheet over the desktop for the length of a vigil.

    It covers the available area, so the taskbar stays reachable, and it never
    takes focus. A left click lifts it; so does the timer running out.
    """

    def __init__(self, rituals, on_lift) -> None:
        super().__init__(None)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._rituals = rituals
        self._on_lift = on_lift
        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._refresh)

    def greet(self) -> None:
        area = QRect()
        for screen in QGuiApplication.screens():
            area = area.united(screen.availableGeometry())
        if area.isNull():
            return
        self.setGeometry(area)
        self.show()
        self._timer.start()
        self.update()

    def lift(self) -> None:
        self._timer.stop()
        if self.isVisible():
            self.hide()

    def _refresh(self) -> None:
        if not self._rituals.focus_active():
            self.lift()
            return
        self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._on_lift()
            event.accept()
            return
        super().mousePressEvent(event)

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(8, 5, 14, 148))
        painter.drawRect(self.rect())

        remaining = self._rituals.focus_remaining()
        clock = f"{remaining // 60:02d}:{remaining % 60:02d}"
        cx = self.width() / 2
        cy = self.height() / 2

        title = QFont("Segoe UI", 20)
        title.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 7.0)
        title.setWeight(QFont.Weight.Light)
        painter.setFont(title)
        painter.setPen(QColor(255, 240, 220, 220))
        painter.drawText(
            QRectF(cx - 220, cy - 96, 440, 40),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            "VIGIL",
        )

        clock_font = QFont("Segoe UI", 44)
        clock_font.setWeight(QFont.Weight.Thin)
        painter.setFont(clock_font)
        painter.setPen(QColor(255, 226, 186, 245))
        painter.drawText(
            QRectF(cx - 220, cy - 50, 440, 84),
            Qt.AlignmentFlag.AlignCenter,
            clock,
        )

        hint = QFont("Segoe UI", 10)
        painter.setFont(hint)
        painter.setPen(QColor(255, 240, 220, 135))
        painter.drawText(
            QRectF(cx - 220, cy + 52, 440, 24),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            "click to lift the veil, or wait",
        )
        painter.end()


class WhisperBox(QWidget):
    """One line of intention. Enter keeps it, Escape lets it go."""

    def __init__(self, on_done) -> None:
        super().__init__(None)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setFixedSize(280, 58)
        self._on_done = on_done
        self._edit = QLineEdit(self)
        self._edit.setGeometry(14, 12, 252, 34)
        self._edit.setMaxLength(80)
        self._edit.setPlaceholderText("A line to keep")
        self._edit.returnPressed.connect(self._commit)
        self._edit.setStyleSheet(
            "QLineEdit {"
            " background: rgba(255, 255, 255, 0.06);"
            " color: #fff6ea;"
            " border: none;"
            " border-radius: 8px;"
            " padding: 4px 8px;"
            " font: 10pt 'Segoe UI';"
            "}"
        )

    def open_at(self, text: str, anchor: QPoint) -> None:
        self._edit.setText(text)
        self._edit.selectAll()
        screen = QApplication.screenAt(anchor) or QApplication.primaryScreen()
        geo = screen.availableGeometry() if screen is not None else QRect(0, 0, 1280, 720)
        x = min(max(geo.left() + 8, anchor.x()), geo.right() - self.width() - 8)
        y = min(max(geo.top() + 8, anchor.y() - self.height() - 8), geo.bottom() - self.height() - 8)
        self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()
        self._edit.setFocus()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            return
        super().keyPressEvent(event)

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QColor(255, 214, 160, 90))
        painter.setBrush(QColor(22, 16, 34, 235))
        painter.drawRoundedRect(1, 1, self.width() - 2, self.height() - 2, 14, 14)
        painter.end()

    def _commit(self) -> None:
        text = self._edit.text().strip()[:80]
        self.hide()
        self._on_done(text)


class TalkBox(QWidget):
    """A compact, temporary conversation with the current buddy."""

    def __init__(self, on_done) -> None:
        super().__init__(None)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setFixedSize(390, 292)
        self._on_done = on_done
        self._buddy_name = "Buddy"
        self._title = QLabel(self)
        self._title.setGeometry(16, 12, 278, 25)
        self._title.setStyleSheet("color:#fff3e5; font: 600 11pt 'Segoe UI';")
        self._history = QPlainTextEdit(self)
        self._history.setGeometry(14, 47, 362, 184)
        self._history.setReadOnly(True)
        self._history.setMaximumBlockCount(48)
        self._history.setStyleSheet(
            "QPlainTextEdit { background:rgba(255,255,255,0.035); color:#f6f1e8;"
            " border:1px solid rgba(255,214,160,35); border-radius:10px;"
            " padding:8px; font:10pt 'Segoe UI'; selection-background-color:#765078; }"
        )
        self._edit = QLineEdit(self)
        self._edit.setGeometry(14, 242, 282, 36)
        self._edit.setMaxLength(MAX_QUESTION)
        self._edit.returnPressed.connect(self._commit)
        self._edit.setPlaceholderText("Type a short message…")
        self._edit.setStyleSheet(
            "QLineEdit {"
            " background: rgba(255, 255, 255, 0.06);"
            " color: #fff6ea;"
            " border: 1px solid rgba(255,214,160,45);"
            " border-radius: 10px;"
            " padding: 4px 10px;"
            " font: 10pt 'Segoe UI';"
            "}"
        )
        self._send = QPushButton("Send", self)
        self._send.setGeometry(304, 242, 72, 36)
        self._send.clicked.connect(self._commit)
        self._send.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send.setStyleSheet(
            "QPushButton { background:rgba(255,186,122,50); color:#fff6ea;"
            " border:1px solid rgba(255,214,160,85); border-radius:10px;"
            " font:600 9pt 'Segoe UI'; }"
            "QPushButton:hover { background:rgba(255,186,122,90); }"
        )
        self._end = QPushButton("×", self)
        self._end.setGeometry(344, 9, 34, 30)
        self._end.setToolTip("Close conversation")
        self._end.setCursor(Qt.CursorShape.PointingHandCursor)
        self._end.setStyleSheet(
            "QPushButton {"
            " background: rgba(255, 120, 120, 40); color: #fff6ea;"
            " border: 1px solid rgba(255, 214, 160, 55); border-radius: 9px;"
            " font: 14pt 'Segoe UI';"
            "}"
            "QPushButton:hover { background: rgba(255, 120, 120, 95); }"
        )
        self._end.clicked.connect(self._end_chat)

    def open_at(self, anchor: QPoint, buddy_name: str) -> None:
        self._buddy_name = buddy_name
        self._title.setText(f"A little chat with {buddy_name}")
        self._history.clear()
        self._history.appendPlainText(f"{buddy_name}: Hi! What are you thinking about?")
        self._edit.clear()
        screen = QApplication.screenAt(anchor) or QApplication.primaryScreen()
        geo = screen.availableGeometry() if screen is not None else QRect(0, 0, 1280, 720)
        x = min(max(geo.left() + 8, anchor.x() - self.width() // 2), geo.right() - self.width() - 8)
        below = anchor.y() + 12
        above = anchor.y() - self.height() - 10
        y = below if below + self.height() <= geo.bottom() - 8 else above
        y = min(max(geo.top() + 8, y), geo.bottom() - self.height() - 8)
        self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()
        self._edit.setFocus()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self._end_chat()
            return
        super().keyPressEvent(event)

    def hideEvent(self, event) -> None:  # noqa: N802
        # A conversation is only kept in this panel and discarded when closed.
        self._edit.clear()
        self._history.clear()
        super().hideEvent(event)

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QColor(255, 214, 160, 90))
        painter.setBrush(QColor(22, 16, 34, 238))
        painter.drawRoundedRect(1, 1, self.width() - 2, self.height() - 2, 15, 15)
        painter.end()

    def _commit(self) -> None:
        text = clean_text(self._edit.text(), MAX_QUESTION)
        if not text:
            self._edit.clear()
            return
        self._edit.clear()
        self._history.appendPlainText(f"You: {text}")
        answer = self._on_done(text)
        if answer:
            self._history.appendPlainText(f"{self._buddy_name}: {answer}")
        else:
            self._history.appendPlainText(
                f"{self._buddy_name}: I got a little tangled. Try one short question?"
            )
        self._edit.setFocus()

    def _end_chat(self) -> None:
        self._edit.clear()
        self.hide()


class CustomizeDialog(QDialog):
    """Nickname, chattiness, and the two animation switches."""

    CHATTER = (("quiet", "Quiet"), ("balanced", "Balanced"), ("chatty", "Chatty"))

    def __init__(self, parent, buddy_name: str, values: dict) -> None:
        super().__init__(parent)
        self.setWindowTitle("Customize buddy")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setMinimumWidth(360)
        self.setStyleSheet(
            "QDialog { background: #161022; }"
            "QLabel { color: #f6f1e8; font: 10pt 'Segoe UI'; }"
            "QLabel#hint { color: rgba(246, 241, 232, 150); font: 9pt 'Segoe UI'; }"
            "QLineEdit, QComboBox {"
            " background: rgba(255, 255, 255, 0.07); color: #fff6ea;"
            " border: 1px solid rgba(255, 214, 160, 60); border-radius: 7px;"
            " padding: 5px 8px; font: 10pt 'Segoe UI';"
            "}"
            "QCheckBox { color: #f6f1e8; font: 10pt 'Segoe UI'; padding: 3px; }"
            "QPushButton {"
            " background: rgba(255, 176, 90, 40); color: #fff6ea;"
            " border: 1px solid rgba(255, 214, 160, 80); border-radius: 8px;"
            " padding: 6px 16px; font: 10pt 'Segoe UI';"
            "}"
            "QPushButton:hover { background: rgba(255, 176, 90, 75); }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(9)

        title = QLabel("Make it yours")
        title.setStyleSheet("font: 600 13pt 'Segoe UI'; color: #ffe2bd;")
        layout.addWidget(title)
        hint = QLabel("Changes stay on this computer.")
        hint.setObjectName("hint")
        layout.addWidget(hint)

        def section(text: str) -> QLabel:
            label = QLabel(text)
            label.setStyleSheet(
                "font: 600 9pt 'Segoe UI'; color: #ffc79a; margin-top: 6px;"
            )
            return label

        layout.addWidget(section("Companion"))
        form = QFormLayout()
        form.setSpacing(8)
        self.name_edit = QLineEdit()
        self.name_edit.setMaxLength(16)
        self.name_edit.setPlaceholderText(buddy_name)
        self.name_edit.setText(str(values.get("nickname", "")))
        form.addRow("Call them", self.name_edit)

        self.chatter_box = QComboBox()
        for key, label in self.CHATTER:
            self.chatter_box.addItem(label, key)
        index = self.chatter_box.findData(values.get("chatter", "balanced"))
        self.chatter_box.setCurrentIndex(max(0, index))
        form.addRow("Small talk", self.chatter_box)
        layout.addLayout(form)

        layout.addWidget(section("Look"))
        look = QFormLayout()
        look.setSpacing(8)
        self.coat_box = QComboBox()
        for key in COAT_ORDER:
            self.coat_box.addItem(COAT_LABELS[key], key)
        coat_index = self.coat_box.findData(values.get("coat", "natural"))
        self.coat_box.setCurrentIndex(max(0, coat_index))
        self.coat_box.setToolTip("A tint mixed into this buddy's fur and trim.")
        look.addRow("Coat", self.coat_box)
        self.glass_box = QComboBox()
        for key in PALETTE_ORDER:
            self.glass_box.addItem(PALETTE_LABELS[key], key)
        glass_index = self.glass_box.findData(values.get("palette", "amber"))
        self.glass_box.setCurrentIndex(max(0, glass_index))
        self.glass_box.setToolTip("The lantern, ring, and plate colours.")
        look.addRow("Glass", self.glass_box)
        layout.addLayout(look)

        layout.addWidget(section("Everyday"))
        self.auto_talk = QCheckBox("Occasional small talk while you work")
        self.auto_talk.setChecked(bool(values.get("auto_talk", False)))
        layout.addWidget(self.auto_talk)
        self.animations = QCheckBox("Let the buddy fidget and fly about")
        self.animations.setChecked(bool(values.get("idle_animations", True)))
        layout.addWidget(self.animations)
        self.sparkles = QCheckBox("Show typing sparks and click ripples")
        self.sparkles.setChecked(bool(values.get("mirror_particles", True)))
        layout.addWidget(self.sparkles)

        layout.addWidget(section("Focus timer"))
        self.dim_focus = QCheckBox("Dim the desk while the timer runs")
        self.dim_focus.setChecked(bool(values.get("dim_focus", True)))
        self.dim_focus.setToolTip("The veil appears with a timer and lifts when it ends.")
        layout.addWidget(self.dim_focus)

        layout.addWidget(section("Windows"))
        self.launch = QCheckBox("Start with Windows when you sign in")
        self.launch.setChecked(bool(values.get("launch_at_start", False)))
        if autostart.supported():
            self.launch.setToolTip("Adds one per-user startup entry. Turning this off removes it.")
        else:
            self.launch.setEnabled(False)
            self.launch.setToolTip("This switch is for Windows only.")
        layout.addWidget(self.launch)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> dict:
        return {
            "nickname": self.name_edit.text(),
            "chatter": str(self.chatter_box.currentData()),
            "coat": str(self.coat_box.currentData()),
            "palette": str(self.glass_box.currentData()),
            "auto_talk": self.auto_talk.isChecked(),
            "idle_animations": self.animations.isChecked(),
            "mirror_particles": self.sparkles.isChecked(),
            "dim_focus": self.dim_focus.isChecked(),
            "launch_at_start": self.launch.isChecked(),
        }


class WardrobeDialog(QDialog):
    """Earned accessories, with the locked ones and their requirements visible."""

    def __init__(
        self,
        parent,
        display_name: str,
        minutes: float,
        sessions: int,
        streak: int,
        equipped: str,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{display_name}'s wardrobe")
        self.setMinimumSize(420, 520)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setStyleSheet(
            "QDialog { background: #161022; }"
            "QLabel { color: #f6f1e8; font: 10pt 'Segoe UI'; }"
            "QLabel#hint { color: rgba(246, 241, 232, 150); font: 9pt 'Segoe UI'; }"
            "QScrollArea { border: 1px solid rgba(255, 214, 160, 40); border-radius: 9px; }"
            "QWidget#list { background: transparent; }"
            "QRadioButton { color: #f6f1e8; font: 10pt 'Segoe UI'; padding: 6px 4px; }"
            "QRadioButton:disabled { color: rgba(246, 241, 232, 105); }"
            "QPushButton {"
            " background: rgba(255, 176, 90, 40); color: #fff6ea;"
            " border: 1px solid rgba(255, 214, 160, 80); border-radius: 8px;"
            " padding: 6px 16px; font: 10pt 'Segoe UI';"
            "}"
            "QPushButton:hover { background: rgba(255, 176, 90, 75); }"
        )
        earned = rewards.unlocked(minutes, sessions, streak)
        earned_keys = {item.key for item in earned}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(8)
        title = QLabel("Wardrobe")
        title.setStyleSheet("font: 600 13pt 'Segoe UI'; color: #ffe2bd;")
        layout.addWidget(title)
        summary = QLabel(
            f"{len(earned)} of {len(rewards.ACCESSORIES)} unlocked · "
            f"{int(minutes)} focus minutes · {sessions} session{'s' if sessions != 1 else ''} · "
            f"{streak}-day streak"
        )
        summary.setObjectName("hint")
        layout.addWidget(summary)
        following = rewards.next_locked(minutes, sessions, streak)
        if following is not None:
            nxt = QLabel(f"Next up: {following.label} — {following.requirement()}")
            nxt.setObjectName("hint")
            layout.addWidget(nxt)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        body.setObjectName("list")
        rows = QVBoxLayout(body)
        rows.setContentsMargins(10, 8, 10, 8)
        rows.setSpacing(2)
        self._group = QButtonGroup(self)
        self._buttons: dict[str, QRadioButton] = {}
        for item in rewards.ACCESSORIES:
            row = QRadioButton(item.label)
            if item.key not in earned_keys:
                row.setText(f"{item.label}  ·  {item.requirement()}")
                row.setEnabled(False)
            row.setToolTip(item.hint or item.requirement())
            row.setChecked(item.key == equipped)
            self._group.addButton(row)
            self._buttons[item.key] = row
            rows.addWidget(row)
        rows.addStretch(1)
        scroll.setWidget(body)
        layout.addWidget(scroll, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selection(self) -> str:
        for key, button in self._buttons.items():
            if button.isChecked():
                return key
        return "none"


class FocusLogDialog(QDialog):
    """This week's finished sessions, grouped by day."""

    def __init__(self, parent, entries: list[str], current: int, best: int) -> None:
        super().__init__(parent)
        self.setWindowTitle("Focus log")
        self.setMinimumSize(420, 430)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setStyleSheet(
            "QDialog { background: #161022; }"
            "QLabel { color: #f6f1e8; font: 10pt 'Segoe UI'; }"
            "QLabel#hint { color: rgba(246, 241, 232, 155); font: 9pt 'Segoe UI'; }"
            "QPlainTextEdit {"
            " background: rgba(255, 255, 255, 0.045); color: #f6f1e8;"
            " border: 1px solid rgba(255, 214, 160, 40); border-radius: 9px;"
            " padding: 8px; font: 10pt 'Segoe UI';"
            "}"
            "QPushButton {"
            " background: rgba(255, 176, 90, 40); color: #fff6ea;"
            " border: 1px solid rgba(255, 214, 160, 80); border-radius: 8px;"
            " padding: 6px 16px; font: 10pt 'Segoe UI';"
            "}"
            "QPushButton:hover { background: rgba(255, 176, 90, 75); }"
        )
        rows = focus_history.week(entries)
        sessions = sum(row["sessions"] for row in rows)
        minutes = sum(row["minutes"] for row in rows)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(8)
        title = QLabel("Focus log")
        title.setStyleSheet("font: 600 13pt 'Segoe UI'; color: #ffe2bd;")
        layout.addWidget(title)
        summary = QLabel(
            f"This week: {sessions} session{'s' if sessions != 1 else ''} · "
            f"{minutes} min · {current}-day streak (best {best})"
        )
        summary.setObjectName("hint")
        layout.addWidget(summary)

        self.body = QPlainTextEdit()
        self.body.setReadOnly(True)
        lines: list[str] = []
        for row in rows:
            day = row["day"]
            label = day.strftime("%a %d %b")
            if row["sessions"]:
                lines.append(
                    f"{label}  ·  {row['sessions']} session{'s' if row['sessions'] != 1 else ''}"
                    f"  ·  {row['minutes']} min"
                )
                for clock, minutes_done in row["times"]:
                    lines.append(f"      {clock}   {minutes_done} min")
            else:
                lines.append(f"{label}  ·  no sessions")
        self.body.setPlainText("\n".join(lines))
        layout.addWidget(self.body, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class CompanionWindow(QWidget):
    def __init__(self, *, listen: bool = True) -> None:
        super().__init__()
        # Custom manifests must be on the roster before saved settings are
        # validated, or a saved custom id would look like an unknown buddy.
        try:
            install_custom_buddies()
        except Exception:
            log.warning("Custom buddies could not be loaded", exc_info=True)
        self.settings: Settings = load_settings()
        # Never let a hand-edited settings file wear an accessory that was not earned.
        current_streak, _best = focus_history.streak(self.settings.focus_log)
        self.settings.accessory = rewards.owned_accessory(
            self.settings.accessory,
            self.settings.focus_minutes_total,
            self.settings.focus_sessions,
            current_streak,
        )
        self._rng = random.Random()
        self._pulse: Pulse | None = None
        self._phase = 0.4
        self._dragging = False
        self._drag_offset = QPoint()
        self._placed = False
        self._down = False
        self._pending_line: str | None = None
        self._celebrate_until = 0.0
        self._hush_from = 0.0
        self._hush_until = 0.0
        self._clock = time.monotonic()
        self._glimmer_dirty = 0.0
        self._last_glimmer_save = time.monotonic()
        self._snap_from = QPoint()
        self._snap_to = QPoint()
        self._snap_i = 0
        self._trick: Trick | None = None
        self._trick_from = QPoint()
        self._trick_amp = (0.0, 0.0)
        self._trick_started = 0.0
        self._trick_spin = 0.0
        self._trick_sparkle = 0.0
        self._trick_gesture = ""
        self._trick_progress = 0.0
        self._trick_next_at = time.monotonic() + self._rng.uniform(15.0, 35.0)
        self._last_focus_tick = -1

        self._judge = ActivityJudge()
        self._activity = (
            self.settings.activity_pin
            if self.settings.activity_pin in (STUDY, GAMING, WORK, CHILL)
            else CHILL
        )
        self._chatter = Chatter(min_gap=self._chatter_gap())
        self._mirror = Mirror()
        self._last_tick = time.monotonic()
        self._ambient_at = time.monotonic()
        self._last_pulse_at = time.monotonic()
        self._next_smalltalk_at = time.monotonic() + 45.0
        self._long_noted = False
        self._late_noted = False
        self._press_at: QPoint | None = None
        self._greeted = False
        self._look_x = 0.0
        self._look_y = 0.0

        tray_ok = QSystemTrayIcon.isSystemTrayAvailable()
        # A ghost perch with no tray has no way back. Refuse that lock-out.
        if self.settings.click_through and not tray_ok:
            self.settings.click_through = False

        self.setWindowTitle("DeskCompy")
        self.setWindowFlags(_window_flags(tool=tray_ok))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setFixedSize(CANVAS_W, CANVAS_H)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        self._note = LanternNote()
        self._whisper = WhisperBox(self._set_intention)
        self._talk = TalkBox(self._answer_question)
        self._sprites = SpriteLibrary(
            folders=custom_dirs() + asset_dirs(),
            character=self.settings.character,
        )
        self.rituals = RitualClock(self.settings, self)
        self._veil = VigilVeil(self.rituals, self._on_veil_lifted)
        self._veil_dismissed = False
        self.tracker = InputTracker(self)

        self._build_actions()
        self._tray: QSystemTrayIcon | None = None
        if tray_ok:
            self._build_tray()

        self.tracker.pulse.connect(self._on_pulse)
        self.tracker.beat.connect(self._on_beat)
        self.tracker.failed.connect(self._on_tracker_failed)
        self.rituals.focus_finished.connect(self._on_focus_finished)
        self.rituals.water_due.connect(self._on_water)
        self.rituals.updated.connect(self._on_rituals_updated)

        self._anim = QTimer(self)
        self._anim.setInterval(90)
        self._anim.timeout.connect(self._tick)
        self._anim.start()

        self._snap = QTimer(self)
        self._snap.setInterval(16)
        self._snap.timeout.connect(self._snap_step)

        self._trick_timer = QTimer(self)
        self._trick_timer.setInterval(16)
        self._trick_timer.timeout.connect(self._trick_step)

        self._refresh_labels()
        self._apply_icon()
        if listen:
            self.tracker.start()

    # --- menus ----------------------------------------------------------

    def _build_actions(self) -> None:
        self.act_today = QAction("Today", self)
        self.act_today.setEnabled(False)
        self.act_activity = QAction("Hanging out", self)
        self.act_activity.setEnabled(False)
        self.act_activity.setToolTip(
            "Read from typing and clicking rhythm. Pin a mode under Activity."
        )
        self.act_show = QAction("Show companion", self)
        self.act_show.triggered.connect(lambda *_: self._bring_back())
        self.act_focus = QAction("Start Focus Timer (25 min)", self)
        self.act_focus.setToolTip("A serious, locked-in session with a countdown watch.")
        self.act_focus.triggered.connect(lambda *_: self._toggle_focus())
        self.act_repeat = QAction("Go again", self)
        self.act_repeat.setToolTip("Start another session at the same length.")
        self.act_repeat.triggered.connect(lambda *_: self._start_focus(self.settings.focus_minutes))
        self.act_custom_timer = QAction("Custom timer…", self)
        self.act_custom_timer.triggered.connect(lambda *_: self._custom_focus())
        self.act_focus_log = QAction("Session log…", self)
        self.act_focus_log.setToolTip("This week's finished sessions and your streak.")
        self.act_focus_log.triggered.connect(lambda *_: self._open_focus_log())
        self._duration_actions: list[QAction] = []
        for minutes in (5, 10, 15, 25, 30, 45, 60):
            action = QAction(f"{minutes} min", self)
            action.triggered.connect(partial(self._start_focus, minutes))
            self._duration_actions.append(action)
        self.act_dim = QAction("Dim the desk during focus", self)
        self.act_dim.setCheckable(True)
        self.act_dim.setChecked(self.settings.dim_focus)
        self.act_dim.setToolTip(
            "The veil now appears with the timer and lifts when it ends."
        )
        self.act_dim.triggered.connect(self._toggle_dim)
        self.act_water = QAction("Water Reminder", self)
        self.act_water.setCheckable(True)
        self.act_water.setChecked(self.settings.water_enabled)
        self.act_water.triggered.connect(self._toggle_water)
        self.act_intention = QAction("Set a line…", self)
        self.act_intention.triggered.connect(lambda *_: self._ask_intention())
        self.act_clear = QAction("Clear the line", self)
        self.act_clear.triggered.connect(lambda *_: self._set_intention(""))
        self.act_mute = QAction("Mute alerts and sounds", self)
        self.act_mute.setToolTip("Silences the chime, focus ticks, and character cues.")
        self.act_mute.setCheckable(True)
        self.act_mute.setChecked(self.settings.muted)
        self.act_mute.triggered.connect(self._toggle_mute)
        self.act_ghost = QAction("Ghost perch", self)
        self.act_ghost.setCheckable(True)
        self.act_ghost.setChecked(self.settings.click_through)
        self.act_ghost.setToolTip("Clicks pass through. Turn this off from the tray icon.")
        self.act_ghost.triggered.connect(self._toggle_ghost)
        self.act_reset = QAction("Reset perch", self)
        self.act_reset.triggered.connect(lambda *_: self._reset_perch())
        self.act_close = QAction("Close Companion", self)
        self.act_close.triggered.connect(lambda *_: self.close())

        self.act_talk = QAction("Talk to buddy…", self)
        self.act_talk.triggered.connect(lambda *_: self._open_talk())
        self.act_trick = QAction("Do a trick now", self)
        self.act_trick.setToolTip("Skip the wait and let the buddy show off.")
        self.act_trick.triggered.connect(lambda *_: self._start_trick(time.monotonic()))
        self.act_wardrobe = QAction("Wardrobe…", self)
        self.act_wardrobe.setToolTip("Accessories earned by finishing focus sessions.")
        self.act_wardrobe.triggered.connect(lambda *_: self._open_wardrobe())
        self.act_customize = QAction("Customize…", self)
        self.act_customize.triggered.connect(lambda *_: self._customize())

        self._activity_group = QActionGroup(self)
        self._activity_group.setExclusive(True)
        self._activity_actions: dict[str, QAction] = {}
        for mode, label in (
            ("auto", "Auto (watch my rhythm)"),
            (STUDY, "Studying"),
            (GAMING, "Gaming"),
            (WORK, "Working"),
            (CHILL, "Hanging out"),
        ):
            action = QAction(label, self)
            action.setCheckable(True)
            action.setChecked(self.settings.activity_pin == mode)
            action.triggered.connect(partial(self._pin_activity, mode))
            self._activity_group.addAction(action)
            self._activity_actions[mode] = action

        self._buddy_group = QActionGroup(self)
        self._buddy_group.setExclusive(True)
        self._buddy_actions: list[QAction] = []
        self._build_buddy_actions()
        self.act_next_buddy = QAction("Next buddy", self)
        self.act_next_buddy.triggered.connect(lambda *_: self._set_character(next_key(self.settings.character)))

        self._palette_group = QActionGroup(self)
        self._palette_group.setExclusive(True)
        self._palette_actions: list[QAction] = []
        for name in PALETTE_ORDER:
            action = QAction(PALETTE_LABELS[name], self)
            action.setCheckable(True)
            action.setChecked(self.settings.palette == name)
            action.triggered.connect(partial(self._set_palette, name))
            self._palette_group.addAction(action)
            self._palette_actions.append(action)

    def _build_buddy_actions(self) -> None:
        for action in self._buddy_actions:
            self._buddy_group.removeAction(action)
            action.deleteLater()
        self._buddy_actions = []
        for key in CHARACTER_ORDER:
            buddy = CHARACTERS[key]
            action = QAction(f"{buddy.name} · {buddy.species}", self)
            action.setCheckable(True)
            action.setChecked(self.settings.character == key)
            # Tooltips render rich text in Qt, so manifest text is escaped.
            action.setToolTip(html_escape(buddy.tagline))
            action.triggered.connect(partial(self._set_character, key))
            self._buddy_group.addAction(action)
            self._buddy_actions.append(action)

    def _fill_menu(self, menu: QMenu, *, include_show: bool) -> None:
        menu.setStyleSheet(MENU_QSS)
        self._refresh_labels()
        if include_show:
            menu.addAction(self.act_show)
        menu.addAction(self.act_activity)
        menu.addAction(self.act_today)
        menu.addSeparator()
        buddies = menu.addMenu("Companion")
        buddies.setStyleSheet(MENU_QSS)
        for action in self._buddy_actions:
            buddies.addAction(action)
        buddies.addSeparator()
        buddies.addAction(self.act_next_buddy)
        activity = menu.addMenu("Activity")
        activity.setStyleSheet(MENU_QSS)
        for action in self._activity_actions.values():
            activity.addAction(action)
        menu.addAction(self.act_talk)
        menu.addAction(self.act_trick)
        menu.addAction(self.act_wardrobe)
        menu.addAction(self.act_customize)
        menu.addSeparator()
        focus = menu.addMenu("Focus")
        focus.setStyleSheet(MENU_QSS)
        focus.addAction(self.act_focus)
        focus.addSeparator()
        for action in self._duration_actions:
            focus.addAction(action)
        focus.addAction(self.act_custom_timer)
        focus.addSeparator()
        focus.addAction(self.act_repeat)
        focus.addAction(self.act_dim)
        focus.addSeparator()
        focus.addAction(self.act_focus_log)
        menu.addAction(self.act_water)
        menu.addSeparator()
        menu.addAction(self.act_intention)
        menu.addAction(self.act_clear)
        glass = menu.addMenu("Glass")
        glass.setStyleSheet(MENU_QSS)
        for action in self._palette_actions:
            glass.addAction(action)
        menu.addSeparator()
        menu.addAction(self.act_mute)
        menu.addAction(self.act_ghost)
        menu.addAction(self.act_reset)
        menu.addSeparator()
        menu.addAction(self.act_close)

    def _build_tray(self) -> None:
        self._tray = QSystemTrayIcon(self)
        self._tray.setIcon(
            build_tray_icon(self.settings.palette, self.settings.character, self.settings.coat)
        )
        self._refresh_tray_menu()
        self._tray.activated.connect(self._tray_activated)
        self._tray.show()
        self._refresh_labels()

    def _refresh_tray_menu(self) -> None:
        if self._tray is None:
            return
        tray_menu = QMenu(self)
        self._fill_menu(tray_menu, include_show=True)
        tray_menu.aboutToShow.connect(self._refresh_labels)
        self._tray.setContextMenu(tray_menu)

    def _popup_menu(self, global_pos: QPoint) -> None:
        menu = QMenu(self)
        self._fill_menu(menu, include_show=False)
        menu.exec(global_pos)

    def _display_name(self) -> str:
        buddy = get_character(self.settings.character)
        return self.settings.nickname or buddy.name

    def _activity_label(self) -> str:
        label = ACTIVITY_LABELS.get(self._activity, "here")
        return f"{label} · set" if self.settings.activity_pin != "auto" else label

    def _chatter_gap(self) -> float:
        return {"quiet": 24.0, "balanced": 9.0, "chatty": 5.0}.get(self.settings.chatter, 9.0)

    def _smalltalk_delay(self) -> float:
        low, high = {
            "quiet": (240.0, 420.0),
            "balanced": (110.0, 200.0),
            "chatty": (55.0, 105.0),
        }.get(self.settings.chatter, (110.0, 200.0))
        return self._rng.uniform(low, high)

    def _refresh_labels(self, *_args) -> None:
        minutes = int(self.settings.glimmer_seconds // 60)
        buddy = get_character(self.settings.character)
        display = self._display_name()
        self.setToolTip(
            html_escape(
                f"{display} · {self._activity_label()} · {minutes} min today"
            )
        )
        streak_now, _best = focus_history.streak(self.settings.focus_log)
        streak_note = f" · {streak_now}-day streak" if streak_now >= 2 else ""
        self.act_today.setText(f"Today: {minutes} min of glimmer{streak_note}")
        self.act_activity.setText(f"{display} · {self._activity_label()}")
        self.act_talk.setText(f"Talk to {display}…")
        for action, key in zip(self._buddy_actions, CHARACTER_ORDER):
            action.setChecked(key == self.settings.character)
        for mode, action in self._activity_actions.items():
            action.setChecked(self.settings.activity_pin == mode)
        if self.rituals.focus_active():
            remaining = self.rituals.focus_remaining()
            self.act_focus.setText(f"End Focus Timer ({remaining // 60}:{remaining % 60:02d})")
        else:
            self.act_focus.setText(f"Start Focus Timer ({self.settings.focus_minutes} min)")
        self.act_repeat.setText(f"Go again ({self.settings.focus_minutes} min)")
        self.act_repeat.setEnabled(not self.rituals.focus_active())
        self.act_dim.setChecked(self.settings.dim_focus)
        earned = rewards.unlocked(
            self.settings.focus_minutes_total, self.settings.focus_sessions, streak_now
        )
        self.act_wardrobe.setText(f"Wardrobe… ({len(earned)}/{len(rewards.ACCESSORIES)})")
        self.act_water.setChecked(self.settings.water_enabled)
        self.act_mute.setChecked(self.settings.muted)
        self.act_ghost.setChecked(self.settings.click_through)
        self.act_trick.setEnabled(self._trick is None)
        self.act_clear.setEnabled(bool(self.settings.intention))
        if self._tray is not None:
            week = glimmer.week_minutes(self.settings)
            self._tray.setToolTip(
                html_escape(
                    f"{display} the {buddy.species}\n"
                    f"{self._activity_label()} with you\n"
                    f"{minutes} min today · {week} min over 7 days"
                )
            )

    def _apply_icon(self) -> None:
        icon = build_tray_icon(
            self.settings.palette, self.settings.character, self.settings.coat
        )
        self.setWindowIcon(icon)
        if self._tray is not None:
            self._tray.setIcon(icon)

    # --- rituals and memory --------------------------------------------

    def _on_rituals_updated(self) -> None:
        if not self.rituals.focus_active() and self._veil.isVisible():
            self._lift_veil()
        if self.rituals.focus_active():
            remaining = self.rituals.focus_remaining()
            if remaining > 0 and remaining % 60 == 0 and remaining != self._last_focus_tick:
                self._last_focus_tick = remaining
                self._play_sound("tick")
        else:
            self._last_focus_tick = -1
        self.update()

    def _start_focus(self, minutes: int) -> None:
        """Begin a session of a chosen length, 5 to 60 minutes."""
        minutes = max(5, min(60, int(minutes)))
        self._cancel_trick()
        self.settings.focus_minutes = minutes
        self.rituals.start_focus(minutes * 60)
        self._veil_dismissed = False
        self._last_focus_tick = minutes * 60
        self._speak("focus_start", force=True)
        if self.settings.dim_focus:
            QTimer.singleShot(0, self._show_veil)
        else:
            self._veil.lift()
        self._save()
        self._refresh_labels()
        self.update()

    def _toggle_focus(self) -> None:
        self._cancel_trick()
        if self.rituals.focus_active():
            self.rituals.cancel_focus()
            self._lift_veil()
            self._say("Vigil set down. Nothing counted.")
        else:
            self._start_focus(self.settings.focus_minutes)
        self._refresh_labels()
        self.update()

    def _custom_focus(self) -> None:
        value = max(5, min(60, int(self.settings.focus_minutes)))
        minutes, accepted = QInputDialog.getInt(
            self, "Focus timer", "Minutes (5–60):", value, 5, 60, 5
        )
        if accepted:
            self._start_focus(minutes)

    def _toggle_dim(self, checked=None) -> None:
        if not isinstance(checked, bool):
            checked = self.act_dim.isChecked()
        self.settings.dim_focus = bool(checked)
        self._save()
        if checked and self.rituals.focus_active():
            self._veil_dismissed = False
            self._show_veil()
        elif not checked:
            self._veil.lift()
        self._refresh_labels()
        self.update()

    def _show_veil(self) -> None:
        if (
            not self.rituals.focus_active()
            or not self.settings.dim_focus
            or self._veil_dismissed
        ):
            return
        self._veil.greet()
        # The moth sits above the sheet so the timer stays visible and draggable.
        self.raise_()
        self._refresh_labels()

    def _lift_veil(self) -> None:
        self._veil.lift()

    def _on_veil_lifted(self) -> None:
        # Lifting the sheet is per-session; dimming stays a timer preference.
        self._veil_dismissed = True
        self._veil.lift()
        self._say("Veil lifted. The timer keeps its own count.")
        self._refresh_labels()

    def _toggle_water(self, checked=None) -> None:
        if not isinstance(checked, bool):
            checked = self.act_water.isChecked()
        self.rituals.set_water_enabled(checked)
        self._say("I'll ask for water each hour." if checked else "Water reminders are quiet.")
        self._refresh_labels()

    def _toggle_mute(self, checked=None) -> None:
        if not isinstance(checked, bool):
            checked = self.act_mute.isChecked()
        self.settings.muted = bool(checked)
        self._save()

    def _toggle_ghost(self, checked=None) -> None:
        if not isinstance(checked, bool):
            checked = self.act_ghost.isChecked()
        if checked and self._tray is None:
            self.act_ghost.setChecked(False)
            self._say("Ghost perch needs the tray icon, so I left it off.")
            return
        self.settings.click_through = bool(checked)
        self._save()
        if checked:
            self._say("Clicks pass through now. The tray icon can bring me back.")

    def _set_palette(self, name: str, _checked: bool = False) -> None:
        if name not in PALETTE_LABELS:
            return
        self.settings.palette = name
        self._save()
        self._apply_icon()
        self.update()

    def _set_character(self, key: str, _checked: bool = False) -> None:
        buddy = get_character(key)
        changed = buddy.key != self.settings.character
        self.settings.character = buddy.key
        self._save()
        if changed:
            self._sprites.set_character(buddy.key)
        self._apply_icon()
        self._mirror.clear()
        self._refresh_labels()
        self.update()
        if changed:
            self._speak("meet", force=True)

    def _ask_intention(self) -> None:
        anchor = self.mapToGlobal(QPoint(0, 0))
        self._whisper.open_at(self.settings.intention, anchor)

    def _set_intention(self, text: str) -> None:
        self.settings.intention = clean_text(text, 80)
        self._save()
        self._refresh_labels()
        self.update()

    def _open_talk(self) -> None:
        self._talk.open_at(
            self.mapToGlobal(QPoint(self.width() // 2, self.height())),
            self._display_name(),
        )

    def _answer_question(self, text: str) -> str | None:
        """Return a local canned reply; the chat panel clears when closed."""
        return converse_reply(self.settings.character, text, self._rng)

    def _pin_activity(self, mode: str, _checked: bool = False) -> None:
        if mode not in ("auto", STUDY, GAMING, WORK, CHILL):
            return
        self.settings.activity_pin = mode
        self._save()
        if mode == "auto":
            self._judge.align(self._activity)
            self._say("Auto mode. I'll read the room again.")
        else:
            label = ACTIVITY_LABELS.get(mode, mode).capitalize()
            if mode != self._activity:
                self._set_activity(mode, force=True, quiet=True)
            self._judge.align(mode)
            self._say(f"Pinned you as {label.lower()}. I'll stop guessing.")
        self._refresh_labels()
        self.update()

    def _customize(self) -> None:
        buddy = get_character(self.settings.character)
        values = {
            "nickname": self.settings.nickname,
            "chatter": self.settings.chatter,
            "coat": self.settings.coat,
            "auto_talk": self.settings.auto_talk,
            "idle_animations": self.settings.idle_animations,
            "mirror_particles": self.settings.mirror_particles,
            "dim_focus": self.settings.dim_focus,
            "launch_at_start": autostart.is_enabled(),
        }
        dialog = CustomizeDialog(self, buddy.name, values)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        chosen = dialog.values()
        self.settings.nickname = clean_text(chosen.get("nickname"), 16)
        chatter = chosen.get("chatter")
        if chatter in ("quiet", "balanced", "chatty"):
            self.settings.chatter = str(chatter)
        self.settings.auto_talk = bool(chosen.get("auto_talk"))
        self.settings.idle_animations = bool(chosen.get("idle_animations"))
        self.settings.mirror_particles = bool(chosen.get("mirror_particles"))
        coat = chosen.get("coat")
        if coat in COAT_LABELS:
            self.settings.coat = str(coat)
        palette = chosen.get("palette")
        if palette in PALETTE_LABELS:
            self.settings.palette = str(palette)
        self.settings.dim_focus = bool(chosen.get("dim_focus", True))
        if not self.settings.dim_focus:
            self._veil.lift()
        elif self.rituals.focus_active():
            self._veil_dismissed = False
            self._show_veil()
        wanted_start = bool(chosen.get("launch_at_start"))
        if autostart.supported() and wanted_start != autostart.is_enabled():
            if not autostart.set_enabled(wanted_start):
                self._say("Windows kept the old startup setting. The log has details.")
        self.settings.launch_at_start = autostart.is_enabled()
        self._chatter.set_min_gap(self._chatter_gap())
        self._next_smalltalk_at = time.monotonic() + 30.0
        self._apply_icon()
        self._save()
        self._refresh_labels()
        self.update()
        if self.settings.nickname:
            self._say(f"Call me {self.settings.nickname}. I like it.")
        else:
            self._say(f"Back to {buddy.name}. Comfortable.")

    def _open_wardrobe(self) -> None:
        streak_now, _best = focus_history.streak(self.settings.focus_log)
        dialog = WardrobeDialog(
            self,
            self._display_name(),
            self.settings.focus_minutes_total,
            self.settings.focus_sessions,
            streak_now,
            self.settings.accessory,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.settings.accessory = rewards.owned_accessory(
            dialog.selection(),
            self.settings.focus_minutes_total,
            self.settings.focus_sessions,
            streak_now,
        )
        self._save()
        self._refresh_labels()
        self.update()
        item = rewards.BY_KEY.get(self.settings.accessory)
        if item is not None and item.key != "none":
            self._say(f"{item.label} it is.")

    def _open_focus_log(self) -> None:
        current, best = focus_history.streak(self.settings.focus_log)
        dialog = FocusLogDialog(self, self.settings.focus_log, current, best)
        dialog.exec()

    def _on_focus_finished(self) -> None:
        minutes = self.rituals.focus_total_minutes()
        before_streak, _best = focus_history.streak(self.settings.focus_log)
        before = rewards.unlocked(
            self.settings.focus_minutes_total, self.settings.focus_sessions, before_streak
        )
        self.settings.focus_log = focus_history.record(self.settings.focus_log, minutes)
        self.settings.focus_sessions += 1
        self.settings.focus_minutes_total += float(minutes)
        streak_now, _best_now = focus_history.streak(self.settings.focus_log)
        after = rewards.unlocked(
            self.settings.focus_minutes_total, self.settings.focus_sessions, streak_now
        )
        gained = rewards.newly_unlocked(before, after)
        if gained:
            # Wear the newest reward right away, so finishing visibly changes.
            self.settings.accessory = gained[0].key
        self._celebrate_until = time.monotonic() + 6.0
        self._lift_veil()
        line = self._chatter.say(
            self.settings.character, "focus_done", now=time.monotonic(), force=True
        ) or f"{minutes} minutes kept. Look up."
        if streak_now >= 2:
            line = f"{line} {streak_now}-day streak."
        if gained:
            line = f"{line} ✦ {gained[0].label} unlocked — check the wardrobe."
        self._alert(line)
        self._save()
        self._refresh_labels()
        self.update()

    def _on_water(self) -> None:
        self._alert_situation("water", "The hour turned. Drink something.")

    def _on_tracker_failed(self, message: str) -> None:
        log.warning(message)
        self._say(message)

    def _on_pulse(self, pulse: object) -> None:
        if not isinstance(pulse, Pulse):
            return
        self._pulse = pulse
        self._last_pulse_at = time.monotonic()
        if self.settings.activity_pin != "auto":
            return
        span = max(1.0, BURST_WINDOW_SECONDS)
        wide_span = max(1.0, float(pulse.wide_seconds or WIDE_WINDOW_SECONDS))
        self._set_activity(
            self._judge.observe(
                pulse.key_count / span,
                pulse.click_count / span,
                pulse.idle_seconds,
                wide_keys=pulse.wide_key_count / wide_span,
                wide_clicks=pulse.wide_click_count / wide_span,
                buckets=pulse.buckets,
            )
        )

    def _set_activity(self, mode: str, *, force: bool = False, quiet: bool = False) -> None:
        if mode == self._activity:
            return
        if self.settings.activity_pin != "auto" and not force:
            return
        previous = self._activity
        self._activity = mode
        self._long_noted = False
        self._judge.reset_clock()
        if not quiet and not self.rituals.focus_active():
            if mode == AWAY:
                self._speak("away")
            elif previous == AWAY:
                self._speak("back")
            else:
                situation = {
                    STUDY: "study",
                    GAMING: "game",
                    WORK: "work",
                    CHILL: "chill",
                }.get(mode)
                if situation:
                    self._speak(situation)
        self._refresh_labels()
        self.update()

    def _on_beat(self, keys: int, clicks: int) -> None:
        if self.settings.mirror_particles:
            if keys > 0:
                self._mirror.typed(keys)
            if clicks > 0:
                self._mirror.clicked()
        self.update()

    def _poke(self) -> None:
        if self.settings.mirror_particles:
            self._mirror.clicked()
        self._speak("poke", force=True)
        self._refresh_labels()
        self.update()

    # --- little performances -------------------------------------------

    def _maybe_trick(self, now: float) -> None:
        """Start a trick now and then, but never while the desk needs quiet."""
        if self._trick is not None or now < self._trick_next_at:
            return
        if (
            not self.settings.idle_animations
            or self.settings.click_through
            or self.rituals.focus_active()
            or self._activity == AWAY
        ):
            self._trick_next_at = now + 30.0
            return
        self._start_trick(now)

    def _start_trick(self, now: float) -> None:
        if self._dragging:
            return
        self._cancel_trick()
        shape = get_character(self.settings.character).body_shape
        pool = list(tricks_for(shape))
        if self._near_edge():
            # Beside a screen edge, peeking and dashing make more sense.
            pool.extend((PEEK, DASH))
        # Signature performances first: a watcher should see the moth hover and
        # the cat groom within a couple of minutes, not once in twenty.
        signature = [item for item in pool if item.gesture]
        if signature and self._rng.random() < 0.7:
            trick = self._rng.choice(signature)
        else:
            trick = self._rng.choice(pool)
        origin = self.pos()
        self._snap.stop()
        self._trick = trick
        self._trick_started = now
        self._trick_from = origin
        self._trick_amp = self._trick_amplitude(trick, origin)
        self._trick_spin = 0.0
        self._trick_sparkle = 0.0
        self._trick_gesture = trick.gesture
        self._trick_progress = 0.0
        if trick.gesture:
            self._play_sound(trick.gesture)
        self._trick_timer.start()
        self._speak("trick")
        self.update()

    def _near_edge(self, margin: float = 150.0) -> bool:
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return False
        geo = screen.availableGeometry()
        return (
            min(
                abs(self.x() - geo.left()),
                abs(geo.right() - (self.x() + self.width())),
                abs(self.y() - geo.top()),
                abs(geo.bottom() - (self.y() + self.height())),
            )
            <= margin
        )

    def _trick_amplitude(self, trick: Trick, origin: QPoint) -> tuple[float, float]:
        """Where and how far this trick carries the perch."""
        screen = self.screen() or QApplication.primaryScreen()
        geo = screen.availableGeometry() if screen is not None else QRect(0, 0, 1280, 720)
        if trick.key == "dash":
            angle = self._rng.uniform(0.0, math.tau)
            reach = self._rng.uniform(90.0, 230.0)
            target_x = origin.x() + math.cos(angle) * reach
            target_y = origin.y() + math.sin(angle) * reach * 0.7
            target_x, target_y = self._clamp_to_screen(round(target_x), round(target_y))
            # If the landing spot is already near an edge, finish flush against
            # it: a desk companion perches on edges, it does not float nearby.
            if self._rng.random() < 0.5:
                if origin.x() < geo.center().x() and target_x - geo.left() < 300:
                    target_x = geo.left() + 6
                elif target_x + self.width() > geo.right() - 300:
                    target_x = geo.right() - self.width() - 6
            return float(target_x - origin.x()), float(target_y - origin.y())
        if trick.key == "peek":
            # Lean toward the nearest side of the screen, then settle back.
            left_gap = origin.x() - geo.left()
            right_gap = geo.right() - (origin.x() + self.width())
            if left_gap <= right_gap:
                return -min(88.0, max(34.0, left_gap + 46.0)), 0.0
            return min(88.0, max(34.0, right_gap + 46.0)), 0.0
        if trick.key == "orbit":
            return self._rng.choice((-1.0, 1.0)) * self._rng.uniform(20.0, 30.0), self._rng.uniform(12.0, 20.0)
        if trick.key == "wiggle":
            return self._rng.uniform(9.0, 16.0), 0.0
        return 0.0, self._rng.uniform(14.0, 22.0)

    def _trick_step(self) -> None:
        trick = self._trick
        if trick is None:
            self._trick_timer.stop()
            return
        progress = (time.monotonic() - self._trick_started) / max(0.1, trick.duration)
        if progress >= 1.0:
            self._finish_trick()
            return
        dx, dy, spin, sparkle = sample_trick(trick.key, progress, self._trick_amp)
        x = round(self._trick_from.x() + dx)
        y = round(self._trick_from.y() + dy)
        self.move(*self._clamp_to_screen(x, y))
        self._trick_spin = spin
        self._trick_sparkle = sparkle
        self._trick_progress = progress
        self.update()

    def _finish_trick(self) -> None:
        trick = self._trick
        self._trick_timer.stop()
        if trick is not None:
            dx, dy, _spin, _sparkle = sample_trick(trick.key, 1.0, self._trick_amp)
            x = round(self._trick_from.x() + dx)
            y = round(self._trick_from.y() + dy)
            self.move(*self._clamp_to_screen(x, y))
        self._trick = None
        self._trick_spin = 0.0
        self._trick_sparkle = 0.0
        self._trick_gesture = ""
        self._trick_progress = 0.0
        self._remember_pos()
        self._trick_next_at = time.monotonic() + self._rng.uniform(30.0, 75.0)
        self.update()

    def _cancel_trick(self) -> None:
        """Stop mid-trick and stay wherever the buddy happens to be."""
        if self._trick is None:
            return
        self._trick_timer.stop()
        self._trick = None
        self._trick_spin = 0.0
        self._trick_sparkle = 0.0
        self._trick_gesture = ""
        self._trick_progress = 0.0
        self._remember_pos()
        self.update()

    def _speak(self, situation: str, *, force: bool = False) -> None:
        line = self._chatter.say(
            self.settings.character,
            situation,
            now=time.monotonic(),
            force=force,
        )
        if line:
            self._say(line)

    def _alert_situation(self, situation: str, fallback: str) -> None:
        line = self._chatter.say(
            self.settings.character,
            situation,
            now=time.monotonic(),
            force=True,
        )
        self._alert(line or fallback)

    def _alert(self, text: str) -> None:
        now = time.monotonic()
        self._hush_from = now
        self._hush_until = now + 1.3
        self._say(text)
        if self.settings.muted:
            return
        if not play_chime():
            QApplication.beep()
        if self._tray is not None:
            self._tray.showMessage("DeskCompy", text, QSystemTrayIcon.MessageIcon.Information, 5000)

    def _play_sound(self, name: str) -> None:
        """Soft cues share the mute switch with alerts; silence is fine."""
        if self.settings.muted:
            return
        sounds.play(name)

    def _say(self, text: str) -> None:
        if not self.isVisible():
            self._pending_line = text
            return
        self._pending_line = None
        buddy = get_character(self.settings.character)
        anchor = self.mapToGlobal(QPoint(self.width() // 2, BODY_Y + 2))
        self._note.present(self._display_name(), text, buddy.accent, anchor)

    def _save(self) -> None:
        self.settings.save()

    def _remember_pos(self) -> None:
        self.settings.x = self.x()
        self.settings.y = self.y()
        self._save()

    def _note_glimmer(self) -> None:
        now = time.monotonic()
        elapsed = min(1.0, now - self._clock)
        self._clock = now
        earning = self.rituals.focus_active() or self._activity in (STUDY, WORK, GAMING)
        if earning:
            glimmer.add_seconds(self.settings, elapsed)
            self._glimmer_dirty += elapsed
        else:
            # Still roll the date over when idle, so yesterday's minutes land
            # in the history instead of waiting for the next burst of work.
            glimmer.add_seconds(self.settings, 0.0)
        if self._glimmer_dirty > 0 and now - self._last_glimmer_save > 20:
            self._glimmer_dirty = 0.0
            self._last_glimmer_save = now
            self._save()
            self._refresh_labels()

    # --- motion ---------------------------------------------------------

    def _tick(self) -> None:
        now = time.monotonic()
        dt = min(0.12, max(0.0, now - self._last_tick))
        self._last_tick = now
        try:
            center = self.mapToGlobal(QPoint(self.width() // 2, BODY_Y))
            pos = QCursor.pos()
            self._look_x = max(-1.0, min(1.0, (pos.x() - center.x()) / 140.0))
            self._look_y = max(-1.0, min(1.0, (pos.y() - center.y()) / 140.0))
        except Exception:
            pass
        visual = self._visual()
        step = {
            SLEEPING: 0.7,
            CALM: 1.5,
            WORKING: 3.0,
            SCATTER: 4.2,
            FOCUS: 1.2,
        }.get(visual, 1.5)
        self._phase = (self._phase + step * dt * 3.2) % 628.0
        if visual == SLEEPING:
            interval = 180
        elif visual == CALM and not self._mirror.busy and self._celebrate() <= 0:
            interval = 90
        else:
            interval = 50
        if self._anim.interval() != interval:
            self._anim.setInterval(interval)
        self._mirror.advance(dt)
        self._note_glimmer()
        # If the hooks are blocked or the tracker stops, no pulses arrive. The
        # buddy should still fall asleep after five quiet minutes.
        if (
            self._activity != AWAY
            and self.settings.activity_pin == "auto"
            and not self.rituals.focus_active()
            and now - self._last_pulse_at >= AWAY_AFTER_SECONDS
        ):
            self._set_activity(AWAY)
        if now - self._ambient_at >= 20.0:
            self._ambient_at = now
            self._ambient()
        self._maybe_trick(now)
        self._maybe_smalltalk(now)
        self.update()

    def _visual(self) -> str:
        if self.rituals.focus_active():
            return FOCUS
        if self._activity == AWAY:
            return SLEEPING
        if self._activity == GAMING:
            return SCATTER
        if self._activity in (STUDY, WORK):
            return WORKING
        return CALM

    def _ambient(self) -> None:
        """Rare, situation-aware lines: long sessions and the small hours."""
        if not self.rituals.focus_active():
            if (
                self._activity in (STUDY, WORK, GAMING)
                and self._judge.minutes() >= 45.0
                and not self._long_noted
            ):
                self._long_noted = True
                self._speak("long")
            hour = time.localtime().tm_hour
            if not self._late_noted and (hour >= 23 or hour < 5):
                self._late_noted = True
                self._speak("late")
            elif self._late_noted and 5 <= hour < 23:
                self._late_noted = False

    def _maybe_smalltalk(self, now: float) -> None:
        """Occasional unprompted chatter, themed to what the desk is doing."""
        if now < self._next_smalltalk_at:
            return
        if not self.settings.auto_talk or self.rituals.focus_active():
            self._next_smalltalk_at = now + 60.0
            return
        if self._activity == AWAY:
            self._next_smalltalk_at = now + 120.0
            return
        if self._note.isVisible():
            self._next_smalltalk_at = now + 20.0
            return
        minutes = self._judge.minutes()
        long_day = self.settings.glimmer_seconds >= 20 * 60
        if self._activity == WORK:
            situation = "work_tired" if minutes >= 4.0 else "work"
        elif self._activity == GAMING:
            situation = "fun" if long_day and self._rng.random() < 0.45 else "game_hype"
        elif self._activity == STUDY:
            situation = "study_grind" if minutes >= 4.0 else "study"
        else:
            situation = (
                "fun" if long_day and self._rng.random() < 0.4 else "smalltalk"
            )
        self._next_smalltalk_at = now + self._smalltalk_delay()
        self._speak(situation)

    def _glow(self) -> float:
        if self._activity == AWAY:
            glow = 0.08
        else:
            glow = 0.28 if self._pulse is None else self._pulse.glow
        if self._visual() == FOCUS:
            glow = max(glow, 0.55)
        glow *= self._hush()
        return min(1.0, glow + 0.25 * self._celebrate() + 0.3 * self._trick_sparkle)

    def _hush(self) -> float:
        """Dip the lantern just before the chime, then let it come back up."""
        now = time.monotonic()
        if now >= self._hush_until:
            return 1.0
        span = max(0.001, self._hush_until - self._hush_from)
        t = min(1.0, max(0.0, (now - self._hush_from) / span))
        return 0.55 + 0.45 * math.cos(math.pi * t)

    def _celebrate(self) -> float:
        if self._celebrate_until <= 0:
            return 0.0
        left = self._celebrate_until - time.monotonic()
        if left <= 0:
            return 0.0
        return min(1.0, left / 6.0)

    def _clock_text(self) -> str | None:
        if not self.rituals.focus_active():
            return None
        remaining = self.rituals.focus_remaining()
        return f"{remaining // 60:02d}:{remaining % 60:02d}"

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        visual = self._visual()
        paint_scene(
            painter,
            self.width(),
            self.height(),
            character=self.settings.character,
            visual=visual,
            phase=self._phase,
            glow=self._glow(),
            focus_progress=self.rituals.focus_progress(),
            water_level=self.rituals.water_level(),
            intention=self.settings.intention,
            sprite=self._sprites.frame(visual),
            palette=self.settings.palette,
            celebrate=self._celebrate(),
            clock_text=self._clock_text(),
            activity_label=self._activity_label(),
            activity=self._activity,
            mirror_typing=self._mirror.typing,
            mirror_clicking=self._mirror.clicking,
            look_x=self._look_x,
            look_y=self._look_y,
            mirror=self._mirror if self.settings.mirror_particles else None,
            history=glimmer.week(self.settings),
            display_name=self._display_name(),
            coat=self.settings.coat,
            accessory=self.settings.accessory,
            animate=self.settings.idle_animations,
            spin=self._trick_spin,
            sparkle=self._trick_sparkle,
            gesture=self._trick_gesture,
            gesture_t=self._trick_progress,
        )
        painter.end()

    def _contains(self, local: QPoint) -> bool:
        shape = get_character(self.settings.character).body_shape
        if shape == "bunny" and QRect(self.width() // 2 - 31, 5, 62, BODY_Y + 8).contains(local):
            return True
        if shape == "owl" and QRect(self.width() // 2 - 44, 28, 88, BODY_Y + 26).contains(local):
            return True
        cx = self.width() / 2
        cy = BODY_Y + 2
        dx = (local.x() - cx) / 76
        dy = (local.y() - cy) / 74
        if dx * dx + dy * dy <= 1.0:
            return True
        if QRect(14, self.height() - 72, self.width() - 28, 60).contains(local):
            return True
        return False

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self._contains(event.position().toPoint()):
            self._cancel_trick()
            self._dragging = True
            self._snap.stop()
            self._press_at = event.globalPosition().toPoint()
            self._drag_offset = self._press_at - self.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._dragging and event.buttons() & Qt.MouseButton.LeftButton:
            pos = event.globalPosition().toPoint() - self._drag_offset
            x, y = self._clamp_to_screen(pos.x(), pos.y())
            self.move(x, y)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._dragging = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            release = event.globalPosition().toPoint()
            tapped = self._press_at is not None and (release - self._press_at).manhattanLength() <= 4
            self._press_at = None
            if tapped:
                self._poke()
            else:
                self._maybe_snap()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self._contains(
            event.position().toPoint()
        ):
            self._open_talk()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event) -> None:  # noqa: N802
        if self.settings.click_through:
            return
        self._popup_menu(event.globalPos())

    def _maybe_snap(self) -> None:
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            self._remember_pos()
            return
        geo = screen.availableGeometry()
        x, y = self.x(), self.y()
        margin = 28
        if abs(x - geo.left()) <= margin:
            x = geo.left() + 8
        elif abs(x + self.width() - geo.right()) <= margin:
            x = geo.right() - self.width() - 8
        if abs(y - geo.top()) <= margin:
            y = geo.top() + 8
        elif abs(y + self.height() - geo.bottom()) <= margin:
            y = geo.bottom() - self.height() - 8
        if (x, y) != (self.x(), self.y()):
            self._snap_from = self.pos()
            self._snap_to = QPoint(x, y)
            self._snap_i = 0
            self._snap.start()
        else:
            self._remember_pos()

    def _snap_step(self) -> None:
        self._snap_i += 1
        t = min(1.0, self._snap_i / 8)
        ease = 1 - (1 - t) ** 3
        x = round(self._snap_from.x() + (self._snap_to.x() - self._snap_from.x()) * ease)
        y = round(self._snap_from.y() + (self._snap_to.y() - self._snap_from.y()) * ease)
        x, y = self._clamp_to_screen(x, y)
        self.move(x, y)
        if t >= 1.0:
            self._snap.stop()
            self._remember_pos()

    def _default_corner(self) -> tuple[int, int]:
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        geo = screen.availableGeometry() if screen is not None else QRect(0, 0, 1280, 720)
        return geo.right() - self.width() - 36, geo.bottom() - self.height() - 48

    def _clamp_to_screen(self, x: int, y: int) -> tuple[int, int]:
        screen = QApplication.screenAt(QPoint(x, y)) or QApplication.primaryScreen()
        geo = screen.availableGeometry() if screen is not None else QRect(0, 0, 1280, 720)
        margin = 8
        x = min(max(geo.left() + margin, x), geo.right() - self.width() - margin)
        y = min(max(geo.top() + margin, y), geo.bottom() - self.height() - margin)
        return x, y

    def _position_visible(self, x: int, y: int) -> bool:
        rect = QRect(x, y, max(40, self.width() // 2), max(40, self.height() // 2))
        return any(rect.intersects(screen.availableGeometry()) for screen in QGuiApplication.screens())

    def _reset_perch(self) -> None:
        self.settings.click_through = False
        self.act_ghost.setChecked(False)
        x, y = self._default_corner()
        x, y = self._clamp_to_screen(x, y)
        self.move(x, y)
        self._remember_pos()
        self.show()
        self.raise_()

    def _bring_back(self) -> None:
        if not self._position_visible(self.x(), self.y()):
            self.move(*self._default_corner())
        x, y = self._clamp_to_screen(self.x(), self.y())
        self.move(x, y)
        self.show()
        self.raise_()

    def _tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._bring_back()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if self._placed:
            return
        self._placed = True
        pending = self._pending_line
        if (
            self.settings.x is not None
            and self.settings.y is not None
            and self._position_visible(self.settings.x, self.settings.y)
        ):
            x, y = self._clamp_to_screen(self.settings.x, self.settings.y)
            self.move(x, y)
        else:
            self.move(*self._default_corner())
        if pending:
            QTimer.singleShot(350, lambda line=pending: self._say(line))
        QTimer.singleShot(900, self._greet)

    def _greet(self) -> None:
        if self._greeted:
            return
        self._greeted = True
        # A startup warning (blocked hooks, for example) gets the first word.
        if self._note.isVisible() or self._pending_line:
            return
        self._speak("meet", force=True)

    def nativeEvent(self, event_type, message):  # noqa: N802
        if sys.platform == "win32":
            try:
                kind = bytes(event_type)
            except Exception:
                kind = b""
            if kind == b"windows_generic_MSG":
                try:
                    msg = ctypes.wintypes.MSG.from_address(int(message))
                    if msg.message == WM_NCHITTEST:
                        # WM_NCHITTEST is sent, not posted, so MSG.pt is stale
                        # here. Ask for the cursor instead; it comes in the
                        # logical coordinates mapFromGlobal expects, even on a
                        # scaled display. Getting this wrong makes the whole
                        # perch click-through, which also swallows drags and
                        # the right-click menu.
                        local = self.mapFromGlobal(QCursor.pos())
                        if self.settings.click_through or not self._contains(local):
                            return True, HTTRANSPARENT
                except Exception:
                    log.debug("Hit-test fell through", exc_info=True)
        # QWidget's SIP wrapper for the base nativeEvent implementation can
        # fault on Windows. An unhandled native message is Qt's default here.
        return False, 0

    def closeEvent(self, event) -> None:  # noqa: N802
        self.shutdown()
        super().closeEvent(event)

    def shutdown(self) -> None:
        if self._down:
            return
        self._down = True
        self._anim.stop()
        self._snap.stop()
        self._trick_timer.stop()
        self._trick = None
        if self.isVisible():
            self.settings.x = self.x()
            self.settings.y = self.y()
        self._glimmer_dirty = 0.0
        self._save()
        self._note.hide()
        self._whisper.hide()
        self._talk.hide()
        self._veil.lift()
        self._mirror.clear()
        self.rituals.stop()
        self.tracker.stop()
        if self._tray is not None:
            self._tray.hide()
