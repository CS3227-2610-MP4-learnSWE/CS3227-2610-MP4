"""Timestamp parsing and formatting shared by the invocation tools."""

from __future__ import annotations

from datetime import datetime, timezone


def parse_utc(value: object) -> datetime | None:
    """ISO text (a trailing `Z` is accepted) as a UTC datetime; None if not text, unparseable or without a timezone."""
    if not isinstance(value, str) or not value:
        return None
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if moment.tzinfo is None or moment.utcoffset() is None:
        return None
    return moment.astimezone(timezone.utc)


def format_utc(value: datetime) -> str:
    """`2026-10-29T01:00:00.123Z`: UTC with milliseconds."""
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
