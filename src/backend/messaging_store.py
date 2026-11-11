"""Transactional review, audience validation and private inbox delivery."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import func, select

from auth.dependencies import current_user, session_context
from auth.lifecycle import lock_account_changes
from auth.rate_limit import admit
from errors import ApiError
from feedback_models import FeedbackForm, FeedbackRecipient, FeedbackResponse
from messaging_errors import fail
from messaging_models import AdminMessage, MessageDelivery, MessagePreview
import messaging_validation as valid
from teacher_materials.models import User
from timestamps import utc_timestamp


def now():
    return datetime.now(timezone.utc)


def begin(db, request, roles):
    # Shared cross-process ordering with login and account disable/archive.
    lock_account_changes(db)
    db.expire_all()
    return current_user(role=roles)(session_context(request, db))


def quota(actor, kind):
    wait = admit(f"messaging:{kind}:{actor.id}", {"read": 20, "preview": 10, "send": 5, "inbox": 60}[kind], 60)
    if wait is not None:
        raise fail("MESSAGING_RATE_LIMITED", retry_after_seconds=wait)


def recipient_json(user):
    return {"id": user.id, "display_name": user.display_name, "role": user.role}


def eligible(db, role):
    return db.scalars(select(User).where(User.role == role, User.access_status == "enabled", User.archived_at.is_(None))).all()


def replyable():
    """SQL conditions for an account a feedback reply can be sent to (one rule for the reply and the follow-up count)."""
    return (User.role.in_(("student", "teacher")), User.access_status == "enabled", User.archived_at.is_(None))


def response_recipient(db, response_id):
    response = db.get(FeedbackResponse, valid.identifier(response_id))
    user = db.scalar(select(User).where(User.id == response.user_id, *replyable())) if response else None
    if user is None:
        raise fail("RECIPIENT_UNAVAILABLE")
    return response, user


def unanswered_response_count(db):
    """Feedback responses from reachable respondents that no sent feedback_response message answers yet."""
    answered = select(AdminMessage.id).where(
        AdminMessage.kind == "feedback_response", AdminMessage.source_feedback_response_id == FeedbackResponse.id
    )
    return db.scalar(
        select(func.count()).select_from(FeedbackResponse).join(User, User.id == FeedbackResponse.user_id).where(*replyable(), ~answered.exists())
    )


def create_preview(db, actor, body):
    kind = body.get("kind")
    if kind == "feedback_response":
        valid.keys(body, {"kind", "response_id", "subject", "body"})
        response, user = response_recipient(db, body["response_id"])
        response_id, role, mode, users = response.id, user.role, None, [user]
    elif kind == "announcement":
        valid.keys(body, {"kind", "audience_role", "audience_mode", "subject", "body"}, {"recipient_ids"})
        role, mode, response_id = body["audience_role"], body["audience_mode"], None
        if type(role) is not str or role not in {"student", "teacher"} or type(mode) is not str or mode not in {"all_active", "selected"}:
            raise fail("INVALID_REQUEST")
        users = eligible(db, role)
        if mode == "selected":
            if "recipient_ids" not in body:
                raise fail("INVALID_RECIPIENTS")
            ids = valid.account_ids(body["recipient_ids"])
            users = [u for u in users if u.id in ids]
            if sorted(u.id for u in users) != ids:
                raise fail("AUDIENCE_CHANGED")
        elif "recipient_ids" in body:
            raise fail("INVALID_REQUEST")
        if not 1 <= len(users) <= 500:
            raise fail("INVALID_RECIPIENTS")
    else:
        raise fail("INVALID_REQUEST")
    stamp = now()
    preview = MessagePreview(id=uuid4(), owner_admin_id=actor.id, kind=kind, feedback_response_id=response_id,
        audience_role=role, audience_mode=mode, subject=valid.text(body["subject"], True), body=valid.text(body["body"]),
        recipients=[recipient_json(u) for u in sorted(users, key=lambda u: u.id)], created_at=stamp, expires_at=stamp + timedelta(minutes=15))
    db.add(preview)
    db.flush()
    return preview_json(preview)


def owned_preview(db, actor, preview_id):
    row = db.scalar(select(MessagePreview).where(MessagePreview.id == valid.identifier(preview_id), MessagePreview.owner_admin_id == actor.id).with_for_update())
    if row is None:
        raise fail("PREVIEW_UNAVAILABLE")
    return row


def preview_json(row):
    return {"id": str(row.id), "kind": row.kind, "response_id": str(row.feedback_response_id) if row.feedback_response_id else None,
        "audience_role": row.audience_role, "audience_mode": row.audience_mode, "subject": row.subject, "body": row.body,
        "recipients": row.recipients, "recipient_count": len(row.recipients), "created_at": utc_timestamp(row.created_at), "expires_at": utc_timestamp(row.expires_at)}


def receipt(db, row):
    sent = db.get(AdminMessage, row.sent_message_id) if row.sent_message_id else None
    return {"message_id": str(sent.id), "preview_id": str(row.id), "kind": sent.kind, "recipient_count": len(row.recipients), "sent_at": utc_timestamp(sent.sent_at)} if sent else None


def require_fresh(row):
    if row.expires_at <= now():
        raise fail("PREVIEW_EXPIRED")


def send(db, actor, row):
    previous = receipt(db, row)
    if previous:
        return previous
    require_fresh(row)
    quota(actor, "send")
    if row.kind == "feedback_response":
        try:
            _, user = response_recipient(db, str(row.feedback_response_id))
        except ApiError as error:
            if error.code == "RECIPIENT_UNAVAILABLE":
                raise fail("AUDIENCE_CHANGED") from None
            raise
        users = [user]
    else:
        users = eligible(db, row.audience_role)
        if row.audience_mode == "selected":
            ids = {u["id"] for u in row.recipients}
            users = [u for u in users if u.id in ids]
    if [recipient_json(u) for u in sorted(users, key=lambda u: u.id)] != row.recipients:
        raise fail("AUDIENCE_CHANGED")
    message = AdminMessage(id=uuid4(), preview_id=row.id, sender_admin_id=actor.id, kind=row.kind,
        source_feedback_response_id=row.feedback_response_id, subject=row.subject, body=row.body, sent_at=now())
    db.add(message)
    db.flush()
    db.add_all([MessageDelivery(id=uuid4(), message_id=message.id, recipient_id=u["id"]) for u in row.recipients])
    row.sent_message_id = message.id
    db.flush()
    return receipt(db, row)


def inbox(db, actor, offset):
    base = select(MessageDelivery, AdminMessage).join(AdminMessage).where(MessageDelivery.recipient_id == actor.id)
    rows = db.execute(base.order_by(AdminMessage.sent_at.desc(), MessageDelivery.id.desc()).offset(offset).limit(21)).all()
    unread = db.scalar(select(func.count()).select_from(MessageDelivery).where(MessageDelivery.recipient_id == actor.id, MessageDelivery.read_at.is_(None)))
    return {"items": [{"id": str(d.id), "kind": m.kind, "subject": m.subject, "body": m.body, "sent_at": utc_timestamp(m.sent_at),
        "read_at": utc_timestamp(d.read_at) if d.read_at else None} for d, m in rows[:20]], "next_offset": offset + 20 if len(rows) > 20 else None, "unread_count": unread}


def unread_summary(db, actor):
    # One statement: both components describe the same database snapshot.
    messages = select(func.count()).select_from(MessageDelivery).where(
        MessageDelivery.recipient_id == actor.id, MessageDelivery.read_at.is_(None)).scalar_subquery()
    requests = select(func.count()).select_from(FeedbackRecipient).join(FeedbackForm).where(
        FeedbackRecipient.user_id == actor.id, FeedbackRecipient.role_snapshot == actor.role,
        FeedbackRecipient.read_at.is_(None), FeedbackForm.state != "draft").scalar_subquery()
    message_count, request_count = db.execute(select(messages, requests)).one()
    return {"unread_count": message_count + request_count,
            "unread_messages": message_count, "unread_requests": request_count}
