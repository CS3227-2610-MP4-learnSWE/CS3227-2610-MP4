"""Pure helpers of the ADM-07 hub: severity, percentiles, rounding and the in-progress rule. No database access."""
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Sequence

from feature_analytics import config


def round_half_up(value: float | Decimal, places: int) -> float:
    return float(Decimal(str(value)).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP))


def rate_percent(part: int, total: int) -> float | None:
    """part / total as a percentage with one decimal, rounded half up on the exact fraction; None without a denominator."""
    if total == 0:
        return None
    return round_half_up(Decimal(part) * 100 / Decimal(total), 1)


def severity(failed: int, total: int, threshold: int = config.LOW_SAMPLE_REQUESTS) -> str | None:
    """low_sample, critical, warning or ok, judged on exact counts; None when there are no requests."""
    if total == 0:
        return None
    if total < threshold:
        return "low_sample"
    if failed * 100 > config.CRITICAL_PERCENT * total:
        return "critical"
    if failed * 100 >= config.WARNING_PERCENT * total:
        return "warning"
    return "ok"


def percentile_nearest_rank(sorted_values: Sequence[int], pct: int) -> int | None:
    """Nearest rank: the element at 1-based position ceil(pct * n / 100) of an ascending list."""
    if not sorted_values:
        return None
    return sorted_values[-(-pct * len(sorted_values) // 100) - 1]


def median_half_up(sorted_values: Sequence[int]) -> int | None:
    """Middle value (mean of the two middle values for an even count) as whole units, half up."""
    n = len(sorted_values)
    if n == 0:
        return None
    mid = n // 2
    return sorted_values[mid] if n % 2 else (sorted_values[mid - 1] + sorted_values[mid] + 1) // 2


def median_one_decimal(sorted_values: Sequence[int]) -> float | None:
    """Middle value (mean of the two middle values for an even count) with one decimal."""
    n = len(sorted_values)
    if n == 0:
        return None
    mid = n // 2
    return float(sorted_values[mid]) if n % 2 else round_half_up((sorted_values[mid - 1] + sorted_values[mid]) / 2, 1)


def finished_state(outcome: str, received_at: datetime, now: datetime) -> str:
    """'success', 'failure' or 'in_progress'. A pending row younger than the expiry is in progress; an older one is a timeout failure."""
    if outcome == "success":
        return "success"
    if outcome == "pending":
        age = now - received_at
        return "in_progress" if age < timedelta(seconds=config.IN_PROGRESS_EXPIRY_S) else "failure"
    return "failure"
