"""Student identity for the practice and companion routes: the signed-in student's session user (SHR-01)."""
from fastapi import Depends

from auth.dependencies import AuthUser, current_user


# One dependency object, so FastAPI looks the session up once per request when a route needs both.
student_user = current_user(role="student")


def require_student(user: AuthUser = Depends(student_user)) -> str:
    """The signed-in student's user id from the session; no header or client value is read."""
    return user.id
