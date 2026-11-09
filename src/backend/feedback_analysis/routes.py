"""ADM-03 endpoints. All use the shared admin check; all data access is filtered by the caller's admin id."""
from functools import wraps

from fastapi import APIRouter, Depends, Request, Response
from fastapi.routing import APIRoute
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from auth.db import get_session
from auth.dependencies import AuthUser, current_user
from errors import ApiError
from llm_client import LlmClient, get_llm_client

from feedback_analysis import config, failures, jobs, service


class AnalysisRoute(APIRoute):
    """Unexpected exceptions become internal_error with a reference; nothing else leaks."""

    def get_route_handler(self):
        original = super().get_route_handler()
        step = "deleting the analysis" if "DELETE" in self.methods else "reading the responses"

        @wraps(original)
        async def handler(request):
            try:
                return await original(request)
            except (ApiError, SQLAlchemyError):
                raise
            except Exception as exc:  # noqa: BLE001
                ref = failures.internal(None, step, exc).details["reference"]
                raise service.error("internal_error", {"reference": ref}, step=step, ref=ref) from None
        return handler


router = APIRouter(prefix="/api/admin/feedback", route_class=AnalysisRoute, tags=["feedback-analysis"])
admin_user = current_user(role="admin")


async def raw_body(request: Request) -> bytes:
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 262144:
            raise service.invalid("too_large")
    return bytes(body)


@router.post("/analyses", status_code=201)
def create_analysis(response: Response, admin: AuthUser = Depends(admin_user), raw: bytes = Depends(raw_body),
                    llm: LlmClient = Depends(get_llm_client), db: Session = Depends(get_session)):
    obj, new_id = service.create(db, admin.id, raw)
    db.close()
    if new_id is None:
        response.status_code = 200
    else:
        jobs.start(new_id, llm)
    return obj


def _page_number(request, name, default, low, high):
    values = request.query_params.getlist(name)
    raw = values[0] if len(values) == 1 else default if not values else None
    if raw is None or len(raw) > 6 or not raw.isascii() or not raw.isdecimal() or not low <= int(raw) <= high:
        raise service.invalid(name)
    return int(raw)


@router.get("/analyses")
def list_analyses(request: Request, admin: AuthUser = Depends(admin_user), db: Session = Depends(get_session)):
    limit = _page_number(request, "limit", str(config.HISTORY_DEFAULT_LIMIT), 1, config.HISTORY_MAX_LIMIT)
    offset = _page_number(request, "offset", "0", 0, 100000)
    return service.history(db, admin.id, limit, offset)


@router.get("/analyses/{analysis_id}")
def get_analysis(analysis_id: str, admin: AuthUser = Depends(admin_user), db: Session = Depends(get_session)):
    return service.get(db, admin.id, analysis_id)


@router.delete("/analyses/{analysis_id}", status_code=204)
def delete_analysis(analysis_id: str, admin: AuthUser = Depends(admin_user), db: Session = Depends(get_session)):
    service.delete_analysis(db, admin.id, analysis_id)
    return Response(status_code=204)


@router.get("/analyses/{analysis_id}/responses/{label}")
def get_evidence(analysis_id: str, label: str, admin: AuthUser = Depends(admin_user), db: Session = Depends(get_session)):
    return service.evidence(db, admin.id, analysis_id, label)


@router.get("/forms/{form_id}/response-count")
def get_response_count(form_id: str, _: AuthUser = Depends(admin_user), db: Session = Depends(get_session)):
    return service.response_count(db, form_id)
