"""Desk rhythm, not a key logger.

pynput's listeners are threads. They only stamp *when* a key goes down or a
button is pressed. Held-key auto-repeat is ignored, the character is never
read, and nothing is written to disk. A Qt timer on the GUI thread folds those
stamps into a state a few times a second, so the window never waits on input.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from threading import Lock

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from states import CALM, SCATTER, SLEEPING, WORKING

# Five minutes with no key and no click.
SLEEP_AFTER_SECONDS = 5 * 60
# Window used to decide "rapidly" / "frequently".
BURST_WINDOW_SECONDS = 5.0
# A second, longer look separates a clicky game from a mixed work session.
WIDE_WINDOW_SECONDS = 30.0
# About eight key-downs in five seconds feels like real typing, not a tap.
RAPID_KEYS = 8
# Four clicks in five seconds is fidgeting or a burst of work.
RAPID_CLICKS = 4
# Stay in Glimmer / Flicker briefly so a pause between words does not strobe.
HOLD_SECONDS = 6.0
# Fast enough that the buddy's mirroring feels live, slow enough to stay cheap.
EVALUATE_EVERY_MS = 250
# Per-second key and click counts, kept for half a minute. The shape of this
# history separates steady note-taking from fast bursts of real work.
BUCKET_SECONDS = 30


@dataclass(frozen=True)
class Pulse:
    state: str
    glow: float
    key_count: int
    click_count: int
    idle_seconds: float
    wide_key_count: int = 0
    wide_click_count: int = 0
    wide_seconds: float = WIDE_WINDOW_SECONDS
    # (keys, clicks) for each of the last 30 seconds, oldest first.
    buckets: tuple[tuple[int, int], ...] = ()


def classify(key_count: int, click_count: int, idle_seconds: float, previous: str) -> str:
    """Map a short burst of input onto sleeping, calm, working, or scatter."""
    if idle_seconds >= SLEEP_AFTER_SECONDS:
        return SLEEPING
    keys_busy = key_count >= RAPID_KEYS
    clicks_busy = click_count >= RAPID_CLICKS
    if keys_busy and clicks_busy:
        return WORKING if key_count >= click_count else SCATTER
    if keys_busy:
        return WORKING
    if clicks_busy:
        return SCATTER
    if previous in (WORKING, SCATTER) and idle_seconds < HOLD_SECONDS:
        return previous
    return CALM


def glow_for(state: str, key_count: int, click_count: int) -> float:
    heat = min(1.0, key_count / 18 + click_count / 12)
    if state == SLEEPING:
        return 0.07
    if state == CALM:
        return 0.24 + 0.12 * heat
    if state == SCATTER:
        return min(1.0, 0.42 + 0.5 * (click_count / 10))
    return min(1.0, 0.38 + 0.62 * max(heat, 0.35))


class InputTracker(QObject):
    """Global cadence listener. Emit Pulse from the Qt thread only."""

    pulse = pyqtSignal(object)
    failed = pyqtSignal(str)
    # Fresh key and click counts since the previous evaluation. Used only to
    # make the buddy bob and sparkle; no key identity is ever recorded.
    beat = pyqtSignal(int, int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._lock = Lock()
        self._events: deque[tuple[float, str]] = deque(maxlen=4096)
        self._held: set[object] = set()
        self._fresh_keys = 0
        self._fresh_clicks = 0
        self._bucket_started = time.monotonic()
        self._bucket_keys = 0
        self._bucket_clicks = 0
        self._buckets: deque[tuple[int, int]] = deque(maxlen=BUCKET_SECONDS)
        self._last_input = time.monotonic()
        self._state = CALM
        self._keyboard = None
        self._mouse = None
        self._timer = QTimer(self)
        self._timer.setInterval(EVALUATE_EVERY_MS)
        self._timer.timeout.connect(self._evaluate)

    def start(self) -> None:
        try:
            from pynput import keyboard, mouse
        except ImportError:
            self.failed.emit("pynput is not installed, so the moth cannot feel the desk.")
            return

        self._keyboard = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
            suppress=False,
        )
        self._mouse = mouse.Listener(on_click=self._on_click, suppress=False)
        self._keyboard.daemon = True
        self._mouse.daemon = True
        try:
            self._keyboard.start()
            self._mouse.start()
        except Exception:
            # One listener may already be running. stop() joins both and drops them.
            self.failed.emit("Input hooks were blocked. The moth will stay in Drift.")
            self.stop()
            return

        self._timer.start()
        QTimer.singleShot(700, self._check_alive)
        self._evaluate()

    def stop(self) -> None:
        self._timer.stop()
        for listener in (self._keyboard, self._mouse):
            if listener is None:
                continue
            try:
                listener.stop()
            except Exception:
                pass
        self._keyboard = None
        self._mouse = None

    def _check_alive(self) -> None:
        listeners = [item for item in (self._keyboard, self._mouse) if item is not None]
        if listeners and any(not item.is_alive() for item in listeners):
            self.failed.emit("The input hook stopped. Rhythm will pause until restart.")

    def _mark(self, kind: str) -> None:
        now = time.monotonic()
        with self._lock:
            self._events.append((now, kind))
            self._last_input = now
            if kind == "key":
                self._fresh_keys += 1
                self._bucket_keys += 1
            else:
                self._fresh_clicks += 1
                self._bucket_clicks += 1
            horizon = now - WIDE_WINDOW_SECONDS
            while self._events and self._events[0][0] < horizon:
                self._events.popleft()

    def _on_press(self, key: object) -> None:
        try:
            with self._lock:
                if key in self._held:
                    return
                self._held.add(key)
        except TypeError:
            pass
        except Exception:
            return
        self._mark("key")

    def _on_release(self, key: object) -> None:
        try:
            with self._lock:
                self._held.discard(key)
        except TypeError:
            pass
        except Exception:
            return

    def _on_click(self, _x: int, _y: int, _button: object, pressed: bool) -> None:
        if not pressed:
            return
        self._mark("click")

    def _capture_seconds(self, now: float) -> None:
        """Roll the current second into the history, filling any quiet ones."""
        elapsed = int(now - self._bucket_started)
        if elapsed <= 0:
            return
        # Quiet seconds first, then the second that just finished, so the
        # deque stays oldest-first for the continuity check.
        for _ in range(min(elapsed, BUCKET_SECONDS) - 1):
            self._buckets.append((0, 0))
        self._buckets.append((self._bucket_keys, self._bucket_clicks))
        self._bucket_started = now
        self._bucket_keys = 0
        self._bucket_clicks = 0

    def _evaluate(self) -> None:
        now = time.monotonic()
        with self._lock:
            self._capture_seconds(now)
            wide_horizon = now - WIDE_WINDOW_SECONDS
            while self._events and self._events[0][0] < wide_horizon:
                self._events.popleft()
            short_horizon = now - BURST_WINDOW_SECONDS
            keys = sum(
                1 for stamp, kind in self._events if kind == "key" and stamp >= short_horizon
            )
            clicks = sum(
                1 for stamp, kind in self._events if kind == "click" and stamp >= short_horizon
            )
            wide_keys = sum(1 for _stamp, kind in self._events if kind == "key")
            wide_clicks = sum(1 for _stamp, kind in self._events if kind == "click")
            fresh_keys, self._fresh_keys = self._fresh_keys, 0
            fresh_clicks, self._fresh_clicks = self._fresh_clicks, 0
            idle = now - self._last_input
            if idle > 2.0 and self._held:
                self._held.clear()
        if fresh_keys or fresh_clicks:
            self.beat.emit(fresh_keys, fresh_clicks)
        state = classify(keys, clicks, idle, self._state)
        self._state = state
        self.pulse.emit(
            Pulse(
                state=state,
                glow=glow_for(state, keys, clicks),
                key_count=keys,
                click_count=clicks,
                idle_seconds=idle,
                wide_key_count=wide_keys,
                wide_click_count=wide_clicks,
                buckets=tuple(self._buckets),
            )
        )
