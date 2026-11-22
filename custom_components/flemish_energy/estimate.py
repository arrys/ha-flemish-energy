"""Calculate a current-rate estimate for one Brussels calendar day."""

from datetime import UTC, date, datetime, time, timedelta
from math import fsum, isfinite
from zoneinfo import ZoneInfo

BRUSSELS = ZoneInfo("Europe/Brussels")


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
