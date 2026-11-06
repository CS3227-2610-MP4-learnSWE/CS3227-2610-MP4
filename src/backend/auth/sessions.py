"""Session lifecycle. Token hashing happens only here."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from auth.models import AuthSession
from auth.lifecycle import lock_account_changes
from errors import ApiError
from teacher_materials.models import User


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def purge_expired(db: Session) -> None:
    db.execute(delete(AuthSession).where(AuthSession.expires_at <= _now()))


def create_session(db: Session, user: User, ttl_seconds: int) -> tuple[str, AuthSession]:
    """New session with a fresh random token. Returns the raw token (cookie value) and the row."""
    lock_account_changes(db)
    db.refresh(user)
    if user.access_status != "enabled":
        raise ApiError(401, "invalid_credentials", "Email or password is incorrect.")
    token = secrets.token_urlsafe(32)
    now = _now()
    row = AuthSession(
        token_hash=hash_token(token),
        user_id=user.id,
        csrf_token=secrets.token_urlsafe(32),
        created_at=now,
        expires_at=now + timedelta(seconds=ttl_seconds),
    )
    purge_expired(db)
    db.add(row)
    db.commit()
    return token, row


def load_session(db: Session, token: str) -> tuple[AuthSession, User] | None:
    """The live session and its user, or None. An expired session is deleted."""
    found = db.execute(
        select(AuthSession, User)
        .join(User, User.id == AuthSession.user_id)
        .where(AuthSession.token_hash == hash_token(token))
        .execution_options(populate_existing=True)
    ).first()
    if found is None:
        return None
    session_row, user = found
    if session_row.expires_at <= _now() or user.access_status != "enabled":
        db.execute(delete(AuthSession).where(AuthSession.id == session_row.id))
        db.commit()
        return None
    return session_row, user


def revoke_session(db: Session, token: str) -> None:
    db.execute(delete(AuthSession).where(AuthSession.token_hash == hash_token(token)))
    db.commit()
