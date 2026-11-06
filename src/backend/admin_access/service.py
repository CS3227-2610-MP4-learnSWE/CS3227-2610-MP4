"""Transactional account lifecycle and membership operations."""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import Request
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from auth.dependencies import AuthUser, current_user, session_context
from auth.lifecycle import lock_account_changes
from auth.models import AuthSession
from errors import ApiError
from teacher_materials.models import Course, CourseMembership, User
from text_validation import is_postgres_text


def account_json(user: User) -> dict:
    return {"id": user.id, "email": user.email, "display_name": user.display_name,
            "role": user.role, "status": user.access_status}


def course_json(course: Course) -> dict:
    return {"id": str(course.id), "title": course.title}


def get_account(db: Session, user_id: str) -> User:
    if not 1 <= len(user_id) <= 64 or not is_postgres_text(user_id):
        raise ApiError(422, "validation_error", "A valid account id is required.")
    user = db.get(User, user_id, populate_existing=True)
    if user is None:
        raise ApiError(404, "not_found", "This account or course is no longer available.")
    return user


def account_detail(db: Session, user: User) -> dict:
    courses = db.scalars(select(Course).join(CourseMembership).where(
        CourseMembership.user_id == user.id).order_by(func.lower(Course.title), Course.id)).all()
    return {"account": account_json(user), "courses": [course_json(course) for course in courses]}


def begin_change(db: Session, request: Request) -> AuthUser:
    lock_account_changes(db)
    # Dependencies may have run before another admin revoked this actor while
    # this transaction waited for the lock. Re-read both session and account.
    db.expire_all()
    return current_user(role="admin")(session_context(request, db))


def require_mutable(user: User) -> None:
    if user.access_status == "archived":
        raise ApiError(409, "account_archived", "Archived accounts cannot be changed.")


def protect_admin(db: Session, actor: AuthUser, user: User) -> None:
    if user.id == actor.id:
        raise ApiError(409, "self_change", "You cannot disable or archive your own account.")
    if user.role == "admin" and user.access_status == "enabled":
        remaining = db.scalar(select(func.count()).select_from(User).where(
            User.role == "admin", User.access_status == "enabled", User.id != user.id))
        if not remaining:
            raise ApiError(409, "last_admin", "At least one enabled administrator must remain.")


def set_status(db: Session, actor: AuthUser, user: User, status: str) -> None:
    require_mutable(user)
    if status == "disabled":
        protect_admin(db, actor, user)
        # Existing teacher writes lock session then user: preserve that order.
        db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
    user.access_status = status
    db.commit()


def archive(db: Session, actor: AuthUser, user: User) -> None:
    protect_admin(db, actor, user)
    if user.access_status == "archived":
        return
    db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
    db.execute(delete(CourseMembership).where(CourseMembership.user_id == user.id))
    user.access_status = "archived"
    user.archived_at = datetime.now(timezone.utc)
    db.commit()


def set_membership(db: Session, user: User, course_id: str, grant: bool) -> None:
    require_mutable(user)
    if user.role not in {"student", "teacher"}:
        raise ApiError(409, "invalid_assignment", "Course access is available only for student and teacher accounts.")
    try:
        parsed = UUID(course_id)
    except ValueError:
        raise ApiError(422, "validation_error", "A valid course id is required.") from None
    if db.get(Course, parsed) is None:
        raise ApiError(404, "not_found", "This account or course is no longer available.")
    if grant:
        db.execute(insert(CourseMembership).values(course_id=parsed, user_id=user.id).on_conflict_do_nothing())
    else:
        db.execute(delete(CourseMembership).where(CourseMembership.course_id == parsed, CourseMembership.user_id == user.id))
    db.commit()
