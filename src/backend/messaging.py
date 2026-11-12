"""Bounded HTTP contract for reviewed administrative inbox messages."""
from functools import wraps

from fastapi import APIRouter, Depends, Request
from fastapi.routing import APIRoute
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from auth.db import get_session
from auth.dependencies import AuthUser, current_user
from errors import ApiError
from messaging_errors import fail
from messaging_models import MessageDelivery
import messaging_store as store
import messaging_validation as valid
from text_validation import is_postgres_text
from timestamps import utc_timestamp


class MessagingRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        @wraps(original)
        async def handler(request):
            try:
                return await original(request)
            except ApiError:
                raise
            except SQLAlchemyError:
                raise fail("MESSAGING_UNAVAILABLE") from None
            except Exception:
                raise fail("MESSAGING_ERROR") from None
        return handler


router = APIRouter(route_class=MessagingRoute, tags=["messaging"])
admin_auth = current_user(role="admin")
recipient_auth = current_user(role=("student", "teacher"))


def admin(request: Request, _: AuthUser = Depends(admin_auth), db: Session = Depends(get_session)):
    actor = store.begin(db, request, "admin")
    if request.method == "GET":
        store.quota(actor, "read")
    return actor


def recipient(request: Request, _: AuthUser = Depends(recipient_auth), db: Session = Depends(get_session)):
    actor = store.begin(db, request, ("student", "teacher"))
    store.quota(actor, "inbox")
    return actor


async def raw_body(request):
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > 131072:
            raise fail("REQUEST_TOO_LARGE")
    return valid.parse(bytes(raw))


async def admin_body(request: Request, _: AuthUser = Depends(admin_auth)):
    return await raw_body(request)


async def recipient_body(request: Request, _: AuthUser = Depends(recipient_auth)):
    return await raw_body(request)


def committed(db, value):
    db.commit()
    return value


@router.get("/api/admin/messaging/feedback-responses/{response_id}/recipient")
def feedback_recipient(response_id: str, request: Request, _: AuthUser = Depends(admin), db: Session = Depends(get_session)):
    valid.query(request)
    response, user = store.response_recipient(db, response_id)
    return committed(db, {"response_id": str(response.id), "recipient": store.recipient_json(user)})


@router.get("/api/admin/messaging/followup-counts")
def followup_counts(request: Request, _: AuthUser = Depends(admin), db: Session = Depends(get_session)):
    valid.query(request)
    return committed(db, {"unanswered_responses": store.unanswered_response_count(db)})


@router.get("/api/admin/messaging/recipients")
def recipients(request: Request, _: AuthUser = Depends(admin), db: Session = Depends(get_session)):
    q = valid.query(request, ("role", "search", "page", "page_size"))
    role, search = q.get("role"), q.get("search", "").strip()
    page = valid.integer(q.get("page", "1"), 1)
    if role not in {"student", "teacher"} or len(search) > 100 or not is_postgres_text(search) or q.get("page_size", "50") != "50":
        raise fail("INVALID_REQUEST")
    users = sorted((u for u in store.eligible(db, role) if search.casefold() in u.display_name.casefold()), key=lambda u: (u.display_name.casefold(), u.id))
    start = (page - 1) * 50
    return committed(db, {"items": [store.recipient_json(u) for u in users[start:start + 50]], "page": page, "page_size": 50, "total": len(users)})


@router.post("/api/admin/messaging/previews", status_code=201)
def preview(request: Request, body: dict = Depends(admin_body), actor: AuthUser = Depends(admin), db: Session = Depends(get_session)):
    valid.query(request)
    store.quota(actor, "preview")
    return committed(db, store.create_preview(db, actor, body))


@router.get("/api/admin/messaging/previews/{preview_id}")
def recover(preview_id: str, request: Request, actor: AuthUser = Depends(admin), db: Session = Depends(get_session)):
    valid.query(request)
    row = store.owned_preview(db, actor, preview_id)
    previous = store.receipt(db, row)
    if previous is None:
        store.require_fresh(row)
    return committed(db, {"preview": store.preview_json(row), "receipt": previous})


@router.post("/api/admin/messaging/previews/{preview_id}/send")
def send(preview_id: str, request: Request, body: dict = Depends(admin_body), actor: AuthUser = Depends(admin), db: Session = Depends(get_session)):
    valid.query(request)
    valid.keys(body, set())
    return committed(db, store.send(db, actor, store.owned_preview(db, actor, preview_id)))


@router.get("/api/messaging/inbox")
def inbox(request: Request, actor: AuthUser = Depends(recipient), db: Session = Depends(get_session)):
    q = valid.query(request, ("limit", "offset"))
    if q.get("limit", "20") != "20":
        raise fail("INVALID_REQUEST")
    return committed(db, store.inbox(db, actor, valid.integer(q.get("offset", "0"))))


@router.get("/api/messaging/unread-count")
def unread_count(request: Request, actor: AuthUser = Depends(recipient), db: Session = Depends(get_session)):
    valid.query(request)
    return committed(db, store.unread_summary(db, actor))


@router.post("/api/messaging/inbox/{delivery_id}/read")
def read(delivery_id: str, request: Request, body: dict = Depends(recipient_body), actor: AuthUser = Depends(recipient), db: Session = Depends(get_session)):
    valid.query(request)
    valid.keys(body, set())
    row = db.scalar(select(MessageDelivery).where(MessageDelivery.id == valid.identifier(delivery_id), MessageDelivery.recipient_id == actor.id).with_for_update())
    if row is None:
        raise fail("MESSAGE_UNAVAILABLE")
    if row.read_at is None:
        row.read_at = store.now()
    return committed(db, {"id": str(row.id), "read_at": utc_timestamp(row.read_at)})
