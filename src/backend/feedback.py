"""Authenticated targeted feedback HTTP contract with bounded transport."""
from functools import wraps
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Request
from fastapi.routing import APIRoute
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from auth.db import get_session
from auth.dependencies import AuthUser, current_user
from auth.rate_limit import admit
from errors import ApiError
from feedback_errors import fail
from feedback_models import FeedbackForm, FeedbackRecipient, FeedbackResponse, FeedbackResponseDraft
import feedback_store as store
import feedback_validation as valid
from study_lessons.models import PublishedLesson
from teacher_materials.models import User
from text_validation import is_postgres_text
from timestamps import utc_timestamp


class FeedbackRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        @wraps(original)
        async def handler(request):
            try:
                return await original(request)
            except ApiError:
                raise
            except SQLAlchemyError:
                raise fail("unavailable") from None
            except Exception:
                # Never expose persistence errors, prompts or private input.
                raise fail("error") from None
        return handler


router = APIRouter(route_class=FeedbackRoute, tags=["feedback"])
admin_user = current_user(role="admin")
recipient_user = current_user(role=("student", "teacher"))


def quota(actor, kind):
    limit = {"read": 120, "write": 60, "draft": 120, "submit": 10}[kind]
    wait = admit(f"feedback:{kind}:{actor.id}", limit, 60)
    if wait is not None:
        raise ApiError(429, "feedback_rate_limited", "Too many feedback requests. Wait before trying again.", retry_after_seconds=wait)


def admin(request: Request, _: AuthUser = Depends(admin_user), db: Session = Depends(get_session)):
    actor = store.begin(db, request, "admin")
    quota(actor, "read" if request.method == "GET" else "write")
    return actor


def recipient(request: Request, _: AuthUser = Depends(recipient_user), db: Session = Depends(get_session)):
    actor = store.begin(db, request, ("student", "teacher"))
    kind = "read" if request.method == "GET" else "draft" if request.url.path.endswith("/draft") else "write"
    quota(actor, kind)
    if request.url.path.endswith("/responses") and request.method == "POST":
        quota(actor, "submit")
    return actor


async def raw_admin(request: Request, _: AuthUser = Depends(admin_user)):
    return await raw_body(request)


async def raw_recipient(request: Request, _: AuthUser = Depends(recipient_user)):
    return await raw_body(request)


async def raw_body(request):
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 262144:
            raise fail("large")
    return bytes(body)


def query(request, allowed=()):
    q = request.query_params
    if any(k not in allowed or len(q.getlist(k)) != 1 for k in q):
        raise fail("input")
    return q


def pagination(request, extra=()):
    q = query(request, ("limit", "offset", *extra))
    values = []
    for key, default, low, high in (("limit", "20", 1, 100), ("offset", "0", 0, 100000)):
        raw = q.get(key, default)
        if len(raw) > 6 or not raw.isascii() or not raw.isdecimal() or not low <= int(raw) <= high:
            raise fail("input")
        values.append(int(raw))
    return (*values, q)


def committed(db, result):
    db.commit()
    return result


@router.get("/api/admin/feedback/forms")
def list_forms(request: Request, _: AuthUser = Depends(admin), db: Session = Depends(get_session)):
    limit, offset, _q = pagination(request)
    rows = db.scalars(select(FeedbackForm).order_by(FeedbackForm.created_at.desc(), FeedbackForm.id).offset(offset).limit(limit + 1)).all()
    return committed(db, store.page(rows, offset, limit, lambda r: store.form_json(db, r, True)))


@router.post("/api/admin/feedback/forms", status_code=201)
def create_form(request: Request, raw: bytes = Depends(raw_admin), actor: AuthUser = Depends(admin), db: Session = Depends(get_session)):
    query(request)
    data = valid.definition(valid.parse(raw))
    store.association(db, data["association"])
    row = FeedbackForm(**data, state="draft", version=1, created_by=actor.id, created_at=store.now(), updated_at=store.now())
    db.add(row)
    db.flush()
    return committed(db, store.form_json(db, row))


@router.get("/api/admin/feedback/associations")
def associations(request: Request, _: AuthUser = Depends(admin), db: Session = Depends(get_session)):
    query(request)
    lessons = db.scalars(select(PublishedLesson).where(PublishedLesson.withdrawn_at.is_(None)).order_by(PublishedLesson.id).limit(501)).all()
    features = [{"id": k, "label": v} for k, v in sorted(valid.FEATURES.items())]
    return committed(db, {"features": features[:500], "lessons": [{"id": str(r.id), "title": r.title} for r in lessons[:500]], "truncated": len(lessons) > 500 or len(features) > 500})


@router.get("/api/admin/feedback/forms/{form_id}")
def get_form(form_id: str, request: Request, _: AuthUser = Depends(admin), db: Session = Depends(get_session)):
    query(request)
    return committed(db, store.form_json(db, store.form(db, form_id)))


@router.put("/api/admin/feedback/forms/{form_id}")
def update_form(form_id: str, request: Request, raw: bytes = Depends(raw_admin), _: AuthUser = Depends(admin), db: Session = Depends(get_session)):
    query(request)
    row = store.form(db, form_id)
    if row.state != "draft":
        raise fail("state")
    body = valid.parse(raw)
    valid.keys(body, {"title", "description", "association", "questions", "version"})
    store.require_version(row, valid.integer(body.pop("version"), 1))
    data = valid.definition(body)
    store.association(db, data["association"])
    for key, value in data.items():
        setattr(row, key, value)
    row.version += 1
    row.updated_at = store.now()
    db.flush()
    return committed(db, store.form_json(db, row))


@router.get("/api/admin/feedback/forms/{form_id}/audience")
def audience(form_id: str, request: Request, _: AuthUser = Depends(admin), db: Session = Depends(get_session)):
    store.form(db, form_id)
    limit, offset, q = pagination(request, ("role", "search"))
    role, search = q.get("role"), q.get("search", "").strip()
    if role not in {"student", "teacher"} or len(search) > 100 or not is_postgres_text(search):
        raise fail("input")
    # Python casefold is deliberately shared with the specified Unicode ordering.
    rows = db.scalars(select(User).where(User.role == role, User.access_status == "enabled")).all()
    rows = sorted((r for r in rows if search.casefold() in r.display_name.casefold()), key=lambda r: (r.display_name.casefold(), r.id))
    return committed(db, store.page(rows[offset:offset + limit + 1], offset, limit, lambda r: {"id": r.id, "display_name": r.display_name, "role": r.role}))


@router.post("/api/admin/feedback/forms/{form_id}/publish")
def publish(form_id: str, request: Request, raw: bytes = Depends(raw_admin), _: AuthUser = Depends(admin), db: Session = Depends(get_session)):
    query(request)
    row = store.form(db, form_id)
    if row.state != "draft":
        raise fail("state")
    body = valid.parse(raw)
    valid.keys(body, {"version", "audience_role", "recipient_ids"})
    store.require_version(row, valid.integer(body["version"], 1))
    ids, role = body["recipient_ids"], body["audience_role"]
    if type(role) is not str or role not in {"student", "teacher"} or type(ids) is not list or not 1 <= len(ids) <= 500:
        raise fail("audience")
    if any(type(i) is not str or not 1 <= len(i) <= 64 or i != i.strip() or not is_postgres_text(i) for i in ids) or len(set(ids)) != len(ids):
        raise fail("audience")
    users = db.scalars(select(User).where(User.id.in_(ids), User.role == role, User.access_status == "enabled")).all()
    if len(users) != len(ids):
        raise fail("audience_changed")
    store.association(db, row.association)
    for user in users:
        db.add(FeedbackRecipient(form_id=row.id, user_id=user.id, role_snapshot=role, display_name_snapshot=user.display_name, inbox_id=uuid4()))
    row.state, row.audience_role, row.published_at = "open", role, store.now()
    row.updated_at = row.published_at
    row.version += 1
    db.flush()
    return committed(db, store.form_json(db, row))


@router.post("/api/admin/feedback/forms/{form_id}/close")
def close(form_id: str, request: Request, raw: bytes = Depends(raw_admin), _: AuthUser = Depends(admin), db: Session = Depends(get_session)):
    query(request)
    row = store.form(db, form_id)
    body = valid.parse(raw)
    valid.keys(body, {"version"})
    version = valid.integer(body["version"], 1)
    if row.state == "draft":
        raise fail("state")
    if row.state != "closed":
        store.require_version(row, version)
        row.state, row.closed_at = "closed", store.now()
        row.updated_at = row.closed_at
        row.version += 1
    db.flush()
    return committed(db, store.form_json(db, row))


@router.get("/api/admin/feedback/forms/{form_id}/responses")
def responses(form_id: str, request: Request, _: AuthUser = Depends(admin), db: Session = Depends(get_session)):
    row = store.form(db, form_id)
    limit, offset, _q = pagination(request)
    rows = db.scalars(select(FeedbackResponse).where(FeedbackResponse.form_id == row.id).order_by(FeedbackResponse.submitted_at.desc(), FeedbackResponse.id).offset(offset).limit(limit + 1)).all()
    return committed(db, store.page(rows, offset, limit, store.response_json))


@router.get("/api/admin/feedback/forms/{form_id}/responses/{response_id}")
def response_detail(form_id: str, response_id: str, request: Request, _: AuthUser = Depends(admin), db: Session = Depends(get_session)):
    query(request)
    form = store.form(db, form_id)
    row = db.get(FeedbackResponse, UUID(valid.uuid(response_id)))
    if row is None or row.form_id != form.id:
        raise fail("missing")
    return committed(db, store.response_json(row, True))


@router.get("/api/feedback/inbox")
def inbox(request: Request, actor: AuthUser = Depends(recipient), db: Session = Depends(get_session)):
    limit, offset, _q = pagination(request)
    base = select(FeedbackRecipient, FeedbackForm).join(FeedbackForm).where(FeedbackRecipient.user_id == actor.id, FeedbackRecipient.role_snapshot == actor.role, FeedbackForm.state != "draft")
    rows = db.execute(base.order_by(FeedbackForm.published_at.desc(), FeedbackRecipient.inbox_id).offset(offset).limit(limit + 1)).all()
    unread = db.scalar(select(func.count()).select_from(FeedbackRecipient).join(FeedbackForm).where(FeedbackRecipient.user_id == actor.id, FeedbackRecipient.read_at.is_(None), FeedbackForm.state != "draft"))
    def render(pair):
        target, form = pair
        submitted = db.scalar(select(FeedbackResponse.id).where(FeedbackResponse.form_id == form.id, FeedbackResponse.user_id == actor.id)) is not None
        draft = db.get(FeedbackResponseDraft, (form.id, actor.id)) is not None
        status = "completed" if submitted else "closed" if form.state == "closed" else "draft" if draft else "not_started"
        return {"id": str(target.inbox_id), "form_id": str(form.id), "title": form.title,
                "created_at": utc_timestamp(form.published_at), "read_at": utc_timestamp(target.read_at) if target.read_at else None,
                "state": form.state, "submitted": submitted, "response_status": status}
    result = store.page(rows, offset, limit, render)
    return committed(db, {**result, "unread_count": unread})


@router.get("/api/feedback/forms/{form_id}")
def respondent_form(form_id: str, request: Request, actor: AuthUser = Depends(recipient), db: Session = Depends(get_session)):
    query(request)
    row, target, response, draft = store.owned(db, form_id, actor)
    if target.read_at is None:
        target.read_at = store.now()
    editable = row.state == "open" and response is None
    result = {"id": str(row.id), "title": row.title, "description": row.description, "association": row.association,
              "state": row.state, "submitted": response is not None, "questions": row.questions if editable else [],
              "draft": store.draft_json(draft) if editable else None}
    return committed(db, result)


@router.put("/api/feedback/forms/{form_id}/draft")
def save_draft(form_id: str, request: Request, raw: bytes = Depends(raw_recipient), actor: AuthUser = Depends(recipient), db: Session = Depends(get_session)):
    query(request)
    row, _target, response, draft = store.owned(db, form_id, actor)
    store.require_open(row, response)
    body = valid.parse(raw)
    valid.keys(body, {"version", "answers"})
    version = valid.integer(body["version"], 0)
    store.require_draft_version(draft, version)
    answers = valid.answers(body["answers"], row.questions, draft=True)
    if draft is None:
        draft = FeedbackResponseDraft(form_id=row.id, user_id=actor.id, version=1, answers=answers, updated_at=store.now())
        db.add(draft)
    else:
        draft.version += 1
        draft.answers, draft.updated_at = answers, store.now()
    db.flush()
    return committed(db, store.draft_json(draft))


@router.post("/api/feedback/forms/{form_id}/responses", status_code=201)
def submit(form_id: str, request: Request, raw: bytes = Depends(raw_recipient), actor: AuthUser = Depends(recipient), db: Session = Depends(get_session)):
    query(request)
    row, _target, response, draft = store.owned(db, form_id, actor)
    store.require_open(row, response)
    body = valid.parse(raw)
    valid.keys(body, {"draft_version", "answers"})
    store.require_draft_version(draft, valid.integer(body["draft_version"], 0))
    answers = valid.answers(body["answers"], row.questions)
    response = FeedbackResponse(form_id=row.id, user_id=actor.id, display_name_snapshot=actor.display_name,
                                submitted_at=store.now(), answers=answers,
                                form_snapshot={"title": row.title, "description": row.description, "association": row.association, "questions": row.questions})
    db.add(response)
    if draft is not None:
        db.delete(draft)
    db.flush()
    return committed(db, {"id": str(response.id), "form_id": str(row.id), "submitted_at": utc_timestamp(response.submitted_at)})
