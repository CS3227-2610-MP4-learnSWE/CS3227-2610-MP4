"""Reporting periods for the teacher overview: allow-list, UTC day boundaries and the `period` JSON object."""
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone

from errors import ApiError
from timestamps import utc_timestamp

PERIODS = ("7d", "30d", "all")
_DAYS = {"7d": 7, "30d": 30}
_WHITESPACE = " \t\r\n\f\v"


@dataclass(frozen=True)
class ReportingPeriod:
    preset: str
    start: datetime | None
    end: datetime


def resolve_period(preset: str, now: datetime) -> ReportingPeriod:
    """Half-open UTC range: today and the previous days, ending at 00:00 UTC tomorrow; `all` has no start."""
    today = now.astimezone(timezone.utc).date()
    end = datetime.combine(today + timedelta(days=1), time.min, tzinfo=timezone.utc)
    days = _DAYS.get(preset)
    start = None if days is None else end - timedelta(days=days)
    return ReportingPeriod(preset, start, end)


def period_json(period: ReportingPeriod) -> dict:
    return {
        "preset": period.preset,
        "start": None if period.start is None else utc_timestamp(period.start),
        "end": utc_timestamp(period.end),
        "start_date": None if period.start is None else period.start.date().isoformat(),
        "end_date": (period.end - timedelta(days=1)).date().isoformat(),
        "timezone": "UTC",
    }


def parse_period(query_params) -> str:
    pairs = list(query_params.multi_items())
    value = pairs[0][1].strip(_WHITESPACE) if len(pairs) == 1 and pairs[0][0] == "period" else None
    if value not in PERIODS:
        raise ApiError(422, "invalid_overview_period", "Choose Last 7 days, Last 30 days or All time.")
    return value
