"""Work out what the desk is doing, from rhythm alone.

The buddy never reads window titles, screens, or the characters you type. It
only sees how fast keys and clicks arrive, which is enough to tell a typing
session from a clicking session and a quiet desk from an abandoned one. Every
rule here is plain Python so it can be tested without a global hook.
"""

from __future__ import annotations

import time

STUDY = "study"
GAMING = "game"
WORK = "work"
CHILL = "chill"
AWAY = "away"

ACTIVITY_LABELS = {
    STUDY: "studying",
    GAMING: "gaming",
    WORK: "working",
    CHILL: "hanging out",
    AWAY: "asleep",
}

# A five-second flurry at this click rate is game-ish rather than somebody
# opening three menus.
GAME_CLICKS_PER_SECOND = 1.2
# Sustained over half a minute, a click *share* this high reads as play even
# when each individual five-second window is below the flurry threshold.
GAME_WIDE_TOTAL = 0.5
GAME_WIDE_CLICKS = 0.2
GAME_WIDE_SHARE = 0.4
# Steady typing with very few clicks reads as study or deep writing.
STUDY_KEYS_PER_SECOND = 0.9
STUDY_CLICK_RATIO = 0.4
STUDY_WIDE_CLICKS = 0.18
# Below this much input in the window, the desk is simply quiet.
BUSY_FLOOR = 0.15
# The original five-minute nap rule.
AWAY_AFTER_SECONDS = 5 * 60
# A new activity must repeat this many evaluations before it is announced, so
# one stray burst of clicks does not flip the whole mood.
CONFIRMATIONS = 2


def classify(
    keys_per_second: float,
    clicks_per_second: float,
    *,
    wide_keys: float | None = None,
    wide_clicks: float | None = None,
) -> str:
    """Map recent input onto an activity. Silence is ``CHILL``.

    ``keys_per_second`` and ``clicks_per_second`` cover the last few seconds.
    The optional wide rates cover roughly half a minute, which catches a game
    played at a modest click speed and separates a typing-heavy task with real
    mouse use from a page-turning study session.

    Cadence cannot identify software. A keyboard-only game and a fast report
    can look identical, so the menu also offers an explicit activity pin.
    """
    keys = max(0.0, float(keys_per_second))
    clicks = max(0.0, float(clicks_per_second))
    wide_keys = keys if wide_keys is None else max(0.0, float(wide_keys))
    wide_clicks = clicks if wide_clicks is None else max(0.0, float(wide_clicks))
    total = keys + clicks
    # A caller that has no long window (an old Pulse, a test) leaves the wide
    # counts at zero. Treat that as "not measured" instead of "perfectly quiet".
    if total > 0 and wide_keys + wide_clicks == 0:
        wide_keys, wide_clicks = keys, clicks
    wide_total = wide_keys + wide_clicks

    if clicks >= GAME_CLICKS_PER_SECOND:
        return GAMING
    if (
        wide_total >= GAME_WIDE_TOTAL
        and wide_clicks >= GAME_WIDE_CLICKS
        and wide_clicks / wide_total >= GAME_WIDE_SHARE
        and total >= 0.35
    ):
        return GAMING
    if keys >= STUDY_KEYS_PER_SECOND and clicks <= max(0.05, keys * STUDY_CLICK_RATIO):
        typing_share = wide_keys / wide_total if wide_total > 0 else 0.0
        if wide_clicks <= STUDY_WIDE_CLICKS and typing_share >= 0.82:
            return STUDY
    if total >= BUSY_FLOOR:
        return WORK
    return CHILL


class ActivityJudge:
    """Stable activity with a little hysteresis, plus a clock for the mood.

    ``observe`` is called a few times a second. It returns the activity that
    should be shown right now, and ``since`` records when that activity began.
    """

    def __init__(self, confirmations: int = CONFIRMATIONS) -> None:
        self.confirmations = max(1, int(confirmations))
        self.mode = CHILL
        self._since = time.monotonic()
        self._candidate = CHILL
        self._streak = 0
        self._started = False

    def observe(
        self,
        keys_per_second: float,
        clicks_per_second: float,
        idle_seconds: float,
        *,
        wide_keys: float | None = None,
        wide_clicks: float | None = None,
        now: float | None = None,
    ) -> str:
        moment = time.monotonic() if now is None else now
        target = (
            AWAY
            if idle_seconds >= AWAY_AFTER_SECONDS
            else classify(
                keys_per_second,
                clicks_per_second,
                wide_keys=wide_keys,
                wide_clicks=wide_clicks,
            )
        )
        if not self._started:
            self._started = True
            self._adopt(target, moment)
            return self.mode
        if target == self.mode:
            self._candidate = target
            self._streak = 0
            return self.mode
        if target != self._candidate:
            self._candidate = target
            self._streak = 1
        else:
            self._streak += 1
        if target == AWAY or self._streak >= self.confirmations:
            self._adopt(target, moment)
        return self.mode

    def _adopt(self, mode: str, moment: float) -> None:
        if mode != self.mode or self._since <= 0:
            self._since = moment
        self.mode = mode
        self._candidate = mode
        self._streak = 0

    def minutes(self, *, now: float | None = None) -> float:
        moment = time.monotonic() if now is None else now
        return max(0.0, (moment - self._since) / 60.0)

    def reset_clock(self, *, now: float | None = None) -> None:
        self._since = time.monotonic() if now is None else now

    def align(self, mode: str, *, now: float | None = None) -> None:
        """Start from a deliberate mode, without waiting for confirmations."""
        moment = time.monotonic() if now is None else now
        self.mode = mode
        self._candidate = mode
        self._streak = 0
        self._started = True
        self._since = moment
