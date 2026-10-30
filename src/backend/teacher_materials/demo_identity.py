"""Explicitly gated, spoofable development identity for teacher demos."""
import os
from uuid import UUID

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from errors import ApiError
from teacher_materials.models import Course, CourseMembership, User


def require_teacher(request: Request, session: Session) -> User:
    if os.getenv("APP_ENV") != "development" or os.getenv("ALLOW_DEMO_IDENTITY", "").lower() != "true":
        raise ApiError(403, "demo_identity_disabled", "Demo teacher identity is disabled.")
    user_id = request.headers.get("X-Demo-User-Id")
    if not user_id:
        raise ApiError(401, "unauthenticated", "Demo user identity is required.")
    user = session.get(User, user_id)
    if user is None:
        raise ApiError(401, "unauthenticated", "Demo user identity is unknown.")
    if user.role != "teacher":
        raise ApiError(403, "forbidden", "Teacher access is required.")
    return user


def require_managed_course(session: Session, teacher: User, course_id: UUID) -> Course:
    course = session.scalar(select(Course).join(CourseMembership, CourseMembership.course_id == Course.id).where(Course.id == course_id, CourseMembership.user_id == teacher.id))
    if course is None:
        raise ApiError(404, "not_found", "Course not found.")
    return course
