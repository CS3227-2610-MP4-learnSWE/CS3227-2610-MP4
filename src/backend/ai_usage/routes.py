"""Authenticated admin aggregate reporting, with strict bounded filters."""
import re
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import SQLAlchemyError

from ai_usage import service
from auth.dependencies import AuthUser, current_user
from auth.rate_limit import admit
from errors import ApiError

router = APIRouter(prefix="/api/admin", tags=["admin"])


def invalid() -> ApiError:
    return ApiError(422, "invalid_ai_usage_filters", "Choose a valid feature and a UTC date range of at most 31 days ending today or earlier.")


class CoverageIn(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    enabled: bool


@router.put("/ai-usage/coverage")
def set_ai_usage_coverage(body: CoverageIn, admin: AuthUser = Depends(current_user(role="admin"))) -> dict:
    """Turn AI usage collection on or off for the integrated features (admin only)."""
    wait = admit(f"ai-usage-coverage:{admin.id}", 10, 60)
    if wait is not None:
        raise ApiError(429, "ai_usage_report_rate_limited", "Too many requests. Try again shortly.", retry_after_seconds=wait)
    try:
        (service.activate_coverage if body.enabled else service.deactivate_coverage)(list(service.INTEGRATED))
    except (SQLAlchemyError, ValueError):
        raise ApiError(503, "ai_usage_unavailable", "AI usage data is temporarily unavailable. Try again.") from None
    return {"enabled": body.enabled}


@router.get("/ai-usage")
def ai_usage(request: Request, admin: AuthUser = Depends(current_user(role="admin"))) -> dict:
    pairs = list(request.query_params.multi_items())
    if len(pairs) != 3 or {key for key, _ in pairs} != {"feature", "start_date", "end_date"}:
        raise invalid()
    values = {key: value.strip(" \t\r\n\f\v") for key, value in pairs}
    if values["feature"] not in ("all", *service.FEATURES):
        raise invalid()
    try:
        if any(not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", values[key]) for key in ("start_date", "end_date")):
            raise ValueError
        start = date.fromisoformat(values["start_date"])
        end = date.fromisoformat(values["end_date"])
        if not 0 <= (end - start).days < 31 or end > datetime.now(timezone.utc).date():
            raise ValueError
    except ValueError:
        raise invalid() from None
    wait = admit(f"ai-usage-report:{admin.id}", 30, 60)
    if wait is not None:
        raise ApiError(429, "ai_usage_report_rate_limited", "Too many report requests. Try again shortly.", retry_after_seconds=wait)
    try:
        return service.read_usage_report(values["feature"], start, end)
    except SQLAlchemyError:
        raise ApiError(503, "ai_usage_unavailable", "AI usage data is temporarily unavailable. Try again.") from None
