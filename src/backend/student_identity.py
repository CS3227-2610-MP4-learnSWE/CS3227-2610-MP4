"""Placeholder student identity: the X-Student-Id header, trimmed. SHR-01 (real login) replaces this module."""
from fastapi import Header

from errors import ApiError


def require_student(x_student_id: str | None = Header(default=None)) -> str:
    student = (x_student_id or "").strip()
    if not student:
        raise ApiError(401, "missing_student", "X-Student-Id header is required.")
    return student
