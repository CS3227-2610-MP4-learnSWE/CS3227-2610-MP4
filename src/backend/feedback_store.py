"""Survey access, snapshots and transactions; all writes share account lock ordering."""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from auth.dependencies import current_user, session_context
from auth.lifecycle import lock_account_changes
from feedback_errors import fail
from feedback_models import FeedbackForm, FeedbackRecipient, FeedbackResponse, FeedbackResponseDraft
from feedback_validation import uuid
from study_lessons.models import PublishedLesson
from timestamps import utc_timestamp


def now():
    return datetime.now(timezone.utc)


def begin(db: Session, request: Request, roles):
    # Same transaction-scoped cross-process lock as account disable/archive and
    # login. Acquire before the feature records; never nest a second connection.
    lock_account_changes(db)
    db.expire_all()
    return current_user(role=roles)(session_context(request, db))


def form(db, raw_id):
    row = db.get(FeedbackForm, UUID(uuid(raw_id)), populate_existing=True)
    if row is None:
        raise fail("missing")
    return row


def owned(db, raw_id, actor):
    row = form(db, raw_id)
    recipient = db.get(FeedbackRecipient, (row.id, actor.id))
    if row.state == "draft" or recipient is None or recipient.role_snapshot != actor.role:
        raise fail("missing")
    response = db.scalar(select(FeedbackResponse).where(FeedbackResponse.form_id == row.id, FeedbackResponse.user_id == actor.id))
    draft = db.get(FeedbackResponseDraft, (row.id, actor.id))
    return row, recipient, response, draft


def require_open(row, response):
    if row.state == "closed":
        raise fail("closed")
    if response is not None:
        raise fail("submitted")


def require_version(row, version):
    if row.version != version:
        raise fail("version")


def require_draft_version(draft, version):
    if (draft.version if draft else 0) != version:
        raise fail("draft_version")


def association(db, value):
    if value and value["kind"] == "lesson":
        lesson = db.get(PublishedLesson, UUID(value["id"]), populate_existing=True)
        if lesson is None or lesson.withdrawn_at is not None:
            raise fail("association")


def form_json(db, row, summary=False):
    result = {"id": str(row.id), "title": row.title, "description": row.description,
              "association": row.association, "questions": row.questions, "state": row.state,
              "version": row.version, "audience_role": row.audience_role,
              "recipient_count": db.scalar(select(func.count()).select_from(FeedbackRecipient).where(FeedbackRecipient.form_id == row.id)),
              "response_count": db.scalar(select(func.count()).select_from(FeedbackResponse).where(FeedbackResponse.form_id == row.id)),
              **{name: utc_timestamp(getattr(row, name)) if getattr(row, name) else None
                 for name in ("created_at", "updated_at", "published_at", "closed_at")}}
    if summary:
        del result["description"]
        del result["questions"]
    return result


def draft_json(draft):
    return {"version": draft.version if draft else 0, "answers": draft.answers if draft else [],
            "updated_at": utc_timestamp(draft.updated_at) if draft else None}


def response_json(row, detail=False):
    result = {"id": str(row.id), "form_id": str(row.form_id),
              "respondent": {"id": row.user_id, "display_name": row.display_name_snapshot},
              "submitted_at": utc_timestamp(row.submitted_at)}
    if detail:
        result.update(form_snapshot=row.form_snapshot, answers=row.answers)
    return result


def page(rows, offset, limit, render):
    return {"items": [render(row) for row in rows[:limit]], "next_offset": offset + limit if len(rows) > limit else None}
