"""The focus log: completed sessions as short strings, plus streaks.

Each entry is ``YYYY-MM-DDTHH:MM|<minutes>``. A list of strings keeps the
settings file flat and easy to validate. Everything here is pure Python.

A streak counts consecutive *days* with at least one completed session. If
today has no session yet, yesterday's streak still stands until the day ends;
missing a whole day breaks it.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

MAX_ENTRIES = 200
MAX_MINUTES = 600


def record(entries: list[str], minutes: int, *, now: datetime | None = None) -> list[str]:
    """Add one finished session, keeping the last ``MAX_ENTRIES``."""
    stamp = now or datetime.now()
    minutes = max(1, min(MAX_MINUTES, int(minutes)))
    entry = f"{stamp:%Y-%m-%dT%H:%M}|{minutes}"
    return (list(entries) + [entry])[-MAX_ENTRIES:]


def parse(entry: str) -> tuple[date, str, int] | None:
    """``(day, HH:MM, minutes)`` or None for anything malformed."""
    try:
        stamp, raw_minutes = entry.split("|", 1)
        moment = datetime.fromisoformat(stamp)
        minutes = int(raw_minutes)
    except (ValueError, AttributeError):
        return None
    if not 1 <= minutes <= MAX_MINUTES:
        return None
    return moment.date(), moment.strftime("%H:%M"), minutes


def day_totals(entries: list[str]) -> dict[date, tuple[int, int]]:
    """day -> (sessions, minutes)."""
    totals: dict[date, tuple[int, int]] = {}
    for entry in entries:
        parsed = parse(entry)
        if parsed is None:
            continue
        day, _clock, minutes = parsed
        sessions, summed = totals.get(day, (0, 0))
        totals[day] = (sessions + 1, summed + minutes)
    return totals


def streak(entries: list[str], *, today: date | None = None) -> tuple[int, int]:
    """``(current streak, best streak)`` in days."""
    key = today or date.today()
    days = sorted(day_totals(entries))
    if not days:
        return 0, 0

    best = 1
    run = 1
    for previous, current in zip(days, days[1:]):
        if current - previous == timedelta(days=1):
            run += 1
            best = max(best, run)
        elif current != previous:
            run = 1

    present = set(days)
    cursor = key if key in present else key - timedelta(days=1)
    current_streak = 0
    while cursor in present:
        current_streak += 1
        cursor -= timedelta(days=1)
    return current_streak, best


def week(entries: list[str], *, today: date | None = None) -> list[dict]:
    """Last seven days, newest first, each with its sessions in the evening first."""
    key = today or date.today()
    totals = day_totals(entries)
    rows: list[dict] = []
    for offset in range(7):
        day = key - timedelta(days=offset)
        sessions, minutes = totals.get(day, (0, 0))
        times = []
        for entry in entries:
            parsed = parse(entry)
            if parsed is not None and parsed[0] == day:
                times.append((parsed[1], parsed[2]))
        times.sort(reverse=True)
        rows.append(
            {
                "day": day,
                "sessions": sessions,
                "minutes": minutes,
                "times": times,
            }
        )
    return rows


def week_totals(entries: list[str], *, today: date | None = None) -> tuple[int, int]:
    rows = week(entries, today=today)
    return sum(row["sessions"] for row in rows), sum(row["minutes"] for row in rows)
