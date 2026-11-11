"""Focus vigil and the hourly glass of water.

Both clocks are QTimers on the GUI thread. They do almost no work: compare
the wall clock and emit. Wall-clock end times mean a laptop sleep does not
freeze the 25 minutes in the middle and then dump every missed second at once.
"""

from __future__ import annotations

import time

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from settings_store import Settings

FOCUS_SECONDS = 25 * 60
WATER_SECONDS = 60 * 60
# If the machine was asleep and we missed water by under ten minutes, ask soon.
# A longer gap (a reboot the next day) starts a fresh hour instead of nagging.
WATER_GRACE_SECONDS = 10 * 60


class RitualClock(QObject):
    focus_finished = pyqtSignal()
    water_due = pyqtSignal()
    updated = pyqtSignal()

    def __init__(self, settings: Settings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self._focus_end: float | None = None
        self._focus_total = FOCUS_SECONDS
        self._last_remaining = -1
        self._prepare_water_schedule()
        self._timer = QTimer(self)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def focus_active(self) -> bool:
        return self._focus_end is not None and time.time() < self._focus_end

    def focus_remaining(self) -> int:
        if self._focus_end is None:
            return 0
        return max(0, int(round(self._focus_end - time.time())))

    def focus_total_minutes(self) -> int:
        """The length of the running (or last) vigil, rounded to whole minutes."""
        return max(1, int(round(self._focus_total / 60)))

    def focus_progress(self) -> float:
        """0 when the vigil starts, 1 when it is over."""
        if not self.focus_active() or self._focus_total <= 0:
            return 0.0
        done = 1.0 - (self.focus_remaining() / self._focus_total)
        return min(1.0, max(0.0, done))

    def start_focus(self, seconds: int = FOCUS_SECONDS) -> None:
        self._focus_total = max(1, int(seconds))
        self._focus_end = time.time() + self._focus_total
        self._last_remaining = self.focus_remaining()
        self.updated.emit()

    def cancel_focus(self) -> None:
        self._focus_end = None
        self._last_remaining = -1
        self.updated.emit()

    def set_water_enabled(self, enabled: bool) -> None:
        self.settings.water_enabled = enabled
        if enabled:
            self.settings.next_water_epoch = time.time() + WATER_SECONDS
        self.settings.save()
        self.updated.emit()

    def water_level(self) -> float | None:
        """How full the dew drop is, from 0 just after a reminder to 1 when due."""
        if not self.settings.water_enabled or not self.settings.next_water_epoch:
            return None
        remaining = self.settings.next_water_epoch - time.time()
        if remaining <= 0:
            return 1.0
        return 1.0 - min(1.0, remaining / WATER_SECONDS)

    def _prepare_water_schedule(self) -> None:
        if not self.settings.water_enabled:
            return
        now = time.time()
        due = self.settings.next_water_epoch
        if due is None:
            self.settings.next_water_epoch = now + WATER_SECONDS
            self.settings.save()
            return
        if due >= now:
            return
        late = now - due
        if late <= WATER_GRACE_SECONDS:
            self.settings.next_water_epoch = now + 8
        else:
            self.settings.next_water_epoch = now + WATER_SECONDS
        self.settings.save()

    def _tick(self) -> None:
        if self._focus_end is not None:
            remaining = self.focus_remaining()
            if remaining <= 0:
                self._focus_end = None
                self._last_remaining = -1
                self.focus_finished.emit()
                self.updated.emit()
            elif remaining != self._last_remaining:
                self._last_remaining = remaining
                self.updated.emit()

        due = self.settings.next_water_epoch
        if self.settings.water_enabled and due is not None and time.time() >= due:
            self.settings.next_water_epoch = time.time() + WATER_SECONDS
            self.settings.save()
            self.water_due.emit()
            self.updated.emit()
