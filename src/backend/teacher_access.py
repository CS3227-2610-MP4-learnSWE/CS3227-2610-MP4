"""Cookie-authenticated teacher transactions and current course access."""
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator
from uuid import UUID

from fastapi import Request
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from auth.dependencies import AuthUser, SessionContext, current_user, require_course_member, session_context, unauthenticated
from auth.csrf import check_csrf
from auth.models import AuthSession
from auth.sessions import hash_token
from auth.settings import load_settings
from errors import ApiError
from teacher_materials.models import CourseMembership, Material, User


def parse_uuid(value: str) -> UUID:
    try:
        if not isinstance(value, str):
            raise TypeError("UUID input must be a string")
        return UUID(value)
    except (ValueError, TypeError) as exc:
        raise ApiError(422, "validation_error", "A valid UUID is required.") from exc


@contextmanager
def teacher_session(request: Request) -> Iterator[tuple[Session, AuthUser]]:
    settings = load_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True, isolation_level="READ COMMITTED")
    try:
        with Session(engine) as session:
            writing = request.method not in {"GET", "HEAD", "OPTIONS"}
            session.info["teacher_write"] = writing
            teacher = current_user(role="teacher")(session_context(request, session))
            if writing:
                # Expired-session cleanup runs before share locks, avoiding DELETE lock upgrades.
                token = request.cookies.get(settings.cookie_name, "")
                row = session.scalar(select(AuthSession).where(AuthSession.token_hash == hash_token(token)).with_for_update(read=True).execution_options(populate_existing=True))
                if row is None or row.user_id != teacher.id:
                    raise unauthenticated()
                user = session.scalar(select(User).where(User.id == row.user_id).with_for_update(read=True).execution_options(populate_existing=True))
                if user is None or row.expires_at <= datetime.now(timezone.utc):
                    raise unauthenticated()
                check_csrf(request, row)
                teacher = current_user(role="teacher")(SessionContext(AuthUser.from_row(user), row.csrf_token))
            yield session, teacher
    except SQLAlchemyError as exc:
        raise ApiError(503, "service_unavailable", "Teacher service is unavailable. Please try again.") from exc
    finally:
        engine.dispose()


def require_managed_course(session: Session, teacher: AuthUser, course_id: UUID):
    if session.info.get("teacher_write"):
        membership = session.scalar(select(CourseMembership).where(CourseMembership.course_id == course_id, CourseMembership.user_id == teacher.id).with_for_update(read=True))
        if membership is None:
            raise ApiError(404, "not_found", "Course not found.")
    return require_course_member(session, teacher, course_id)


def owned_material(session: Session, teacher: AuthUser, material_id: str) -> Material:
    material = session.scalar(select(Material).join(CourseMembership, CourseMembership.course_id == Material.course_id).where(Material.id == parse_uuid(material_id), CourseMembership.user_id == teacher.id))
    if material is None:
        raise ApiError(404, "not_found", "Material not found.")
    require_managed_course(session, teacher, material.course_id)
    return material


def delete_version(request: Request) -> int:
    values = request.query_params.getlist("version")
    value = values[0] if len(values) == 1 else ""
    if not value or not value.isascii() or not value.isdecimal() or len(value) > 100 or int(value) < 1:
        raise ApiError(422, "validation_error", "Provide a positive integer version.")
    return int(value)


def check_version(actual: int, expected: int) -> None:
    if actual != expected:
        raise ApiError(409, "draft_conflict", "This draft has changed. Load the latest saved version before trying again.")


@contextmanager
def commit_deletion(session: Session, *, material: bool = False):
    try:
        yield
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        if getattr(exc.orig, "sqlstate", None) == "23503":
            if material:
                raise ApiError(409, "material_in_use", "Delete the note drafts and MCQ batches referencing this material first.") from None
            raise ApiError(409, "draft_in_use", "This draft is referenced by other content and cannot be deleted.") from None
        raise
