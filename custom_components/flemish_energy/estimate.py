"""Calculate a current-rate estimate for one Brussels calendar day."""

from datetime import UTC, date, datetime, time, timedelta
from math import fsum, isfinite
from zoneinfo import ZoneInfo

BRUSSELS = ZoneInfo("Europe/Brussels")
ELECTRICITY_PUBLICATION_GRACE_DAYS = 2


def day_window(now: datetime, days_ago: int) -> tuple[date, datetime, datetime]:
    """Return the local date and its UTC Recorder boundaries."""
    day = now.astimezone(BRUSSELS).date() - timedelta(days=days_ago)
    start = datetime.combine(day, time.min, BRUSSELS).astimezone(UTC)
    end = datetime.combine(day + timedelta(days=1), time.min, BRUSSELS).astimezone(UTC)
    return day, start, end


def finite_number(value: object) -> float | None:
    """Read a finite numeric value from Recorder or a sensor state."""
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if isfinite(number) else None


def measured_usage(rows) -> float | None:
    """Return energy from published changes, preserving a measured zero."""
    changes = [finite_number(row.get("change")) for row in rows]
    if not changes or None in changes:
        return None
    return fsum(changes)


def latest_published_usage(
    rows, earliest: date, today: date, *, exclude_days: frozenset[date] = frozenset()
) -> tuple[date, float] | None:
    """Find the newest past Brussels day with usable Recorder changes."""
    by_day = {}
    for row in rows:
        timestamp = finite_number(row.get("start"))
        if timestamp is None:
            continue
        day = datetime.fromtimestamp(timestamp, BRUSSELS).date()
        if earliest <= day < today and day not in exclude_days:
            by_day.setdefault(day, []).append(row)

    for day in sorted(by_day, reverse=True):
        if (usage := measured_usage(by_day[day])) is not None:
            return day, usage
    return None


def provisional_electricity_days(import_rows, export_rows, today: date) -> frozenset[date]:
    """Defer recent all-zero grid days while the provider can still revise them."""
    provisional = set()
    for offset in range(1, ELECTRICITY_PUBLICATION_GRACE_DAYS + 1):
        day = today - timedelta(days=offset)
        end = day + timedelta(days=1)
        imported = latest_published_usage(import_rows, day, end)
        exported = latest_published_usage(export_rows, day, end)
        if imported == (day, 0) and exported == (day, 0):
            provisional.add(day)
    return frozenset(provisional)
