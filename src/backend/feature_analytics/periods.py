"""Validation of the reporting period shared by every analytics endpoint."""
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

from errors import ApiError
from feature_analytics import config

_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


@dataclass(frozen=True)
class Window:
    period_start: date
    period_end: date
    start_utc: datetime
    end_utc_exclusive: datetime


def invalid_date() -> ApiError:
    return ApiError(422, "invalid_date", "Enter dates as YYYY-MM-DD.")


def window_for(period_start: date, period_end: date) -> Window:
    """UTC window [period_start 00:00, period_end + 1 day 00:00)."""
    return Window(
        period_start,
        period_end,
        datetime.combine(period_start, time.min, tzinfo=timezone.utc),
        datetime.combine(period_end + timedelta(days=1), time.min, tzinfo=timezone.utc),
    )


def _parse_date(value: str | None) -> date:
    text = (value or "").strip()
    if not _DATE.fullmatch(text):
        raise invalid_date()
    try:
        parsed = date(int(text[:4]), int(text[5:7]), int(text[8:10]))
        parsed + timedelta(days=1)  # the end date needs a following day for the exclusive bound
    except (ValueError, OverflowError):
        raise invalid_date() from None
    return parsed


def parse_period(period_start: str | None, period_end: str | None) -> Window:
    """Rules in order: date format, start <= end, at most MAX_PERIOD_DAYS days. The first failing rule is raised."""
    start = _parse_date(period_start)
    end = _parse_date(period_end)
    if start > end:
        raise ApiError(422, "period_order", "The start date must be on or before the end date.")
    if (end - start).days + 1 > config.MAX_PERIOD_DAYS:
        raise ApiError(422, "period_too_long", "The period can be at most 366 days.")
    return window_for(start, end)


def parse_workflow(value: str | None) -> str:
    text = (value or "").strip()
    if text not in config.WORKFLOWS:
        raise ApiError(422, "invalid_workflow", "Choose student_exercise or teacher_lesson_planning.")
    return text


def _paging_number(value: str | None, default: int, low: int, high: int) -> int:
    if value is None:
        return default
    text = value.strip()
    if not text.isascii() or not text.isdecimal() or len(text) > 9 or not low <= int(text) <= high:
        raise ApiError(422, "invalid_paging", "limit must be 1 to 100 and offset must be 0 or more.")
    return int(text)


def parse_paging(limit: str | None, offset: str | None, default_limit: int | None = None) -> tuple[int, int]:
    return (
        _paging_number(limit, default_limit or config.DEFAULT_PAGE_LIMIT, 1, config.MAX_PAGE_LIMIT),
        _paging_number(offset, 0, 0, 10**9),
    )


def _choice(value: str | None, default: str | None, allowed: tuple[str, ...]) -> str | None:
    if value is None:
        return default
    text = value.strip().lower()
    return text if text in allowed else None


def parse_chatbot_users_query(role: str | None, sort: str | None, order: str | None, limit: str | None,
                              offset: str | None) -> tuple[str, str, str, int, int]:
    """Rules in order: role, sort and order, paging. Returns (role, sort, order, limit, offset)."""
    role_value = _choice(role, None, ("student", "teacher"))
    if role_value is None:
        raise ApiError(422, "invalid_role", "Choose student or teacher.")
    sort_value = _choice(sort, "unsuccessful", config.USERS_SORTS)
    order_value = _choice(order, "desc", config.USERS_ORDERS)
    if sort_value is None or order_value is None:
        raise ApiError(422, "invalid_sort", "Choose a valid sort column and order.")
    page_limit, page_offset = parse_paging(limit, offset, config.CHATBOT_USERS_DEFAULT_LIMIT)
    return role_value, sort_value, order_value, page_limit, page_offset


def parse_include_rows(value: str | None) -> bool:
    text = "true" if value is None else value.strip().lower()
    if text not in ("true", "false"):
        raise ApiError(422, "invalid_include_rows", "include_rows must be true or false.")
    return text == "true"
