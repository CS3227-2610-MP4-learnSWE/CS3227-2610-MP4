"""Access checks shared by the teacher routers: demo identity, course and material ownership."""
import os
from contextlib import contextmanager
from typing import Iterator
from uuid import UUID

from fastapi import Request
from sqlalchemy import create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from errors import ApiError
from teacher_materials.demo_identity import require_demo_enabled, require_teacher
from teacher_materials.models import CourseMembership, Material, User


def parse_uuid(value: str) -> UUID:
    try:
        if not isinstance(value, str):
            raise TypeError("UUID input must be a string")
        return UUID(value)
    except (ValueError, TypeError) as exc:
        raise ApiError(422, "validation_error", "A valid UUID is required.") from exc


@contextmanager
def teacher_session(request: Request) -> Iterator[tuple[Session, User]]:
    require_demo_enabled()
    if not request.headers.get("X-Demo-User-Id"):
        raise ApiError(401, "unauthenticated", "Demo user identity is required.")
    url = os.getenv("DATABASE_URL")
    if not url or not url.startswith("postgresql+psycopg://"):
        raise ApiError(503, "service_unavailable", "Teacher materials service is unavailable.")
    try:
        engine = create_engine(url, pool_pre_ping=True, isolation_level="READ COMMITTED")
        with Session(engine) as session:
            teacher = require_teacher(request, session)
            yield session, teacher
    except SQLAlchemyError as exc:
        raise ApiError(503, "service_unavailable", "Teacher materials service is unavailable.") from exc
    finally:
        if "engine" in locals():
            engine.dispose()


def owned_material(session: Session, teacher: User, material_id: str) -> Material:
    material = session.scalar(select(Material).join(CourseMembership, CourseMembership.course_id == Material.course_id).where(Material.id == parse_uuid(material_id), CourseMembership.user_id == teacher.id))
    if material is None:
        raise ApiError(404, "not_found", "Material not found.")
    return material
