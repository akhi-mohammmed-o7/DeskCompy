"""Today's glimmer, plus a short memory of the last week.

The window counts seconds only while the moth is in Glimmer. When the date
turns, the finished day is folded into ``settings.history`` and the counter
starts again. Everything here is pure Python, so the rules are tested without
opening a window.
"""

from __future__ import annotations

from datetime import date, timedelta

from settings_store import Settings

# Seven bars: six remembered days plus today.
WEEK_DAYS = 7
# Remember a little more than a week so a late save cannot lose a bar.
KEEP_DAYS = 10
MAX_HISTORY = 14


def today_key() -> str:
    return date.today().isoformat()


def _trim(settings: Settings, today: str) -> None:
    try:
        edge = date.fromisoformat(today) - timedelta(days=KEEP_DAYS)
    except ValueError:
        settings.history.clear()
        return
    kept: dict[str, float] = {}
    for key, value in settings.history.items():
        try:
            day = date.fromisoformat(key)
        except ValueError:
            continue
        if day >= edge:
            kept[key] = float(value)
    settings.history = dict(sorted(kept.items())[-MAX_HISTORY:])


def add_seconds(settings: Settings, seconds: float, *, today: str | None = None) -> None:
    """Credit work to today, archiving the previous day if the date turned.

    A zero call still rolls the date, which lets the window keep its history
    honest even when it is idle at midnight.
    """
    key = today or today_key()
    if settings.glimmer_date != key:
        if settings.glimmer_date and settings.glimmer_seconds > 0:
            settings.history[settings.glimmer_date] = float(settings.glimmer_seconds)
        settings.glimmer_date = key
        settings.glimmer_seconds = 0.0
    if seconds <= 0:
        _trim(settings, key)
        return
    settings.glimmer_seconds = float(settings.glimmer_seconds) + float(seconds)
    _trim(settings, key)


def week(settings: Settings, *, today: str | None = None) -> list[tuple[str, float, bool]]:
    """Oldest first: ``(iso_date, seconds, is_today)`` for the last seven days."""
    key = today or today_key()
    try:
        last = date.fromisoformat(key)
    except ValueError:
        return []
    series: list[tuple[str, float, bool]] = []
    for offset in range(WEEK_DAYS - 1, -1, -1):
        day = (last - timedelta(days=offset)).isoformat()
        is_today = day == key
        if is_today:
            seconds = float(settings.glimmer_seconds) if settings.glimmer_date == day else 0.0
        else:
            seconds = float(settings.history.get(day, 0.0))
        series.append((day, max(0.0, seconds), is_today))
    return series


def week_minutes(settings: Settings, *, today: str | None = None) -> int:
    return int(sum(seconds for _day, seconds, _today in week(settings, today=today)) // 60)
