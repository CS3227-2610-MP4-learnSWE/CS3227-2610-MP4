"""Public auth surface for routes: current_user(...) and require_course_member(...).

Identity comes only from the session cookie. No identity header, query or body field is read.
"""
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth.csrf import check_csrf, check_origin
from auth.db import get_session
from auth.sessions import load_session
from auth.settings import load_settings
from errors import ApiError
from teacher_materials.models import Course, CourseMembership, User


@dataclass(frozen=True)
class AuthUser:
    id: str
    email: str | None
    display_name: str
    role: str  # "student" | "teacher" | "admin"

    @classmethod
    def from_row(cls, row: User) -> "AuthUser":
        return cls(id=row.id, email=row.email, display_name=row.display_name, role=row.role)

    def as_json(self) -> dict[str, str | None]:
        return {"id": self.id, "email": self.email, "display_name": self.display_name, "role": self.role}


@dataclass(frozen=True)
class SessionContext:
    user: AuthUser
    csrf_token: str


def unauthenticated() -> ApiError:
    return ApiError(401, "unauthenticated", "Sign in to continue.")


def session_context(request: Request, db: Session = Depends(get_session)) -> SessionContext:
    """401 without a live session; for unsafe methods, 403 csrf_failed on a bad Origin or token."""
    settings = load_settings()
    token = request.cookies.get(settings.cookie_name)
    found = load_session(db, token) if token else None
    if found is None:
        raise unauthenticated()
    session_row, user = found
    check_origin(request, settings)
    check_csrf(request, session_row)
    return SessionContext(AuthUser.from_row(user), session_row.csrf_token)


def current_user(role: str | Iterable[str] | None = None) -> Callable[..., AuthUser]:
    """Dependency factory: Depends(current_user()) or Depends(current_user(role="teacher")).

    Order of failures: 401 unauthenticated, 403 csrf_failed (unsafe methods), 403 forbidden.
    """
    allowed = None if role is None else frozenset([role] if isinstance(role, str) else role)

    def dependency(context: SessionContext = Depends(session_context)) -> AuthUser:
        if allowed is not None and context.user.role not in allowed:
            raise ApiError(403, "forbidden", "You do not have access to this.")
        return context.user

    return dependency


def require_course_member(db: Session, user: AuthUser, course_id: UUID) -> Course:
    """The course when the user has a membership row; the same 404 for missing and not a member."""
    course = db.scalar(
        select(Course)
        .join(CourseMembership, CourseMembership.course_id == Course.id)
        .where(Course.id == course_id, CourseMembership.user_id == user.id)
    )
    if course is None:
        raise ApiError(404, "not_found", "Course not found.")
    return course
