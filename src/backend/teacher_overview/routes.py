"""GET /api/teacher/overview: teacher-only aggregate report with a validated period."""
from fastapi import APIRouter, Request

from auth.rate_limit import admit
from errors import ApiError
from teacher_access import teacher_session
from teacher_overview import service
from teacher_overview.schemas import parse_period, resolve_period

router = APIRouter(prefix="/api/teacher", tags=["teacher overview"])


@router.get("/overview")
def learning_overview(request: Request) -> dict:
    with teacher_session(request) as (db, teacher):
        preset = parse_period(request.query_params)
        wait = admit(f"teacher-overview:{teacher.id}", 30, 60)
        if wait is not None:
            raise ApiError(429, "overview_rate_limited", "Too many overview requests. Try again shortly.", retry_after_seconds=wait)
        now = service.utc_now()
        return service.build_overview(db, teacher.id, resolve_period(preset, now), now)
