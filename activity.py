"""Work out what the desk is doing, from rhythm alone.

The buddy never reads window titles, screens, or the characters you type. It
only sees how fast keys and clicks arrive, and how steady that rhythm is, which
is enough to tell a typing stretch from a clicking session, a slow
note-taking pace from a fast writing one, and a quiet desk from an abandoned
one. Every rule here is plain Python so it can be tested without a global hook.
"""

from __future__ import annotations

import time
from collections.abc import Sequence

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

# A burst of clicking this fast is play, not somebody opening three menus.
# Frantic clicking is the most reliable cadence signal the desk offers.
GAME_CLICK_FLURRY = 1.6
# Sustained over half a minute, this much clicking with little typing reads as
# play even when no single five-second window is a flurry.
GAME_WIDE_CLICKS = 0.5
GAME_WIDE_SHARE = 0.6
GAME_WIDE_TOTAL = 0.7
# Any typing rhythm at all. Below this the desk is mouse-driven.
TYPING_RATE = 0.55
# Swift, continuous typing is work, never studying, even with no mouse at all.
FAST_TYPING = 2.2
# The unhurried end of typing, with an almost-still mouse, reads as study.
STUDY_MAX_KEYS = 1.9
STUDY_MAX_CLICKS = 0.15
STUDY_CONTINUITY = 0.5
STUDY_MAX_CLICK_SHARE = 0.2
# Below this much input in the window, the desk is simply quiet.
BUSY_FLOOR = 0.06
# Five quiet minutes is a nap.
AWAY_AFTER_SECONDS = 5 * 60
# A new activity must repeat this many evaluations before it is announced, so
# one stray burst of clicks does not flip the whole mood. Studying is the
# easiest label to apply by accident, so it takes the longest to earn.
CONFIRMATIONS = 2
CONFIRMATIONS_FOR = {WORK: 3, STUDY: 6, GAMING: 2, CHILL: 1}
# Once the desk is clearly busy, a short think-pause should not empty the mood.
# These are the quiet seconds each activity tolerates before Chill returns.
QUIET_HOLD = {STUDY: 45.0, WORK: 22.0, GAMING: 8.0, CHILL: 0.0}


def typing_continuity(buckets: Sequence[Sequence[int]]) -> float | None:
    """Share of the last twenty seconds that contained at least one key.

    A steady writer touches the keyboard most seconds; somebody reading a
    document mostly clicks. ``None`` means there was not enough history to
    judge, and the caller should fall back to the current rate.
    """
    recent = [bucket for bucket in buckets[-20:] if bucket]
    if len(recent) < 5:
        return None
    active = sum(1 for bucket in recent if int(bucket[0]) > 0)
    return active / len(recent)


def classify(
    keys_per_second: float,
    clicks_per_second: float,
    *,
    wide_keys: float | None = None,
    wide_clicks: float | None = None,
    continuity: float | None = None,
) -> str:
    """Map recent input onto an activity. Silence is ``CHILL``.

    ``keys_per_second`` and ``clicks_per_second`` cover the last few seconds.
    The optional wide rates cover roughly half a minute, and ``continuity`` is
    the share of recent seconds with any typing in them. Together they separate
    a fast writing rhythm from a slow reading-and-notes rhythm, which the raw
    rate alone cannot do.

    Cadence cannot identify software. A keyboard-only game and a fast report
    can look identical, so the menu also offers an explicit activity pin.
    """
    keys = max(0.0, float(keys_per_second))
    clicks = max(0.0, float(clicks_per_second))
    wide_keys = keys if wide_keys is None else max(0.0, float(wide_keys))
    wide_clicks = clicks if wide_clicks is None else max(0.0, float(wide_clicks))
    total = keys + clicks
    # A caller with no long window (an old Pulse, a test) leaves the wide
    # counts at zero. Treat that as "not measured" instead of "perfectly quiet".
    if total > 0 and wide_keys + wide_clicks == 0:
        wide_keys, wide_clicks = keys, clicks
    wide_total = wide_keys + wide_clicks
    click_share = wide_clicks / wide_total if wide_total > 0 else 0.0
    if continuity is None:
        # No history: assume the rhythm was as steady as it looks right now.
        steady = 1.0 if keys >= TYPING_RATE else 0.0
    else:
        steady = min(1.0, max(0.0, float(continuity)))

    # Play first: no other pattern looks like a stream of clicks.
    if clicks >= GAME_CLICK_FLURRY:
        return GAMING
    if (
        wide_clicks >= GAME_WIDE_CLICKS
        and click_share >= GAME_WIDE_SHARE
        and wide_total >= GAME_WIDE_TOTAL
    ):
        return GAMING
    # Fast, confident typing is work. This is the fix for a writing session
    # being announced as studying.
    if keys >= FAST_TYPING:
        return WORK
    if keys >= TYPING_RATE:
        if (
            clicks <= STUDY_MAX_CLICKS
            and click_share <= STUDY_MAX_CLICK_SHARE
            and keys <= STUDY_MAX_KEYS
            and steady >= STUDY_CONTINUITY
        ):
            return STUDY
        return WORK
    if total >= BUSY_FLOOR:
        return WORK
    return CHILL


class ActivityJudge:
    """Stable activity with deliberate hysteresis, plus a clock for the mood.

    ``observe`` is called a few times a second. It returns the activity that
    should be shown right now, and ``minutes`` records how long that activity
    has been going. Leaving a busy activity needs a real pause; entering one
    only needs a moment, except for Studying, which is slow to earn.
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
        buckets: Sequence[Sequence[int]] | None = None,
        now: float | None = None,
    ) -> str:
        moment = time.monotonic() if now is None else now
        continuity = typing_continuity(buckets) if buckets else None
        target = (
            AWAY
            if idle_seconds >= AWAY_AFTER_SECONDS
            else classify(
                keys_per_second,
                clicks_per_second,
                wide_keys=wide_keys,
                wide_clicks=wide_clicks,
                continuity=continuity,
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
        if target == CHILL and idle_seconds < QUIET_HOLD.get(self.mode, 0.0):
            # A breath between paragraphs is not a different afternoon.
            self._candidate = self.mode
            self._streak = 0
            return self.mode
        if target != self._candidate:
            self._candidate = target
            self._streak = 1
        else:
            self._streak += 1
        needed = min(self.confirmations, CONFIRMATIONS_FOR.get(target, self.confirmations))
        if target == AWAY or self._streak >= needed:
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
