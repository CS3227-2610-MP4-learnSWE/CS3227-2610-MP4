"""Admin-only endpoints. All parsing follows shared session/CSRF/role checks."""
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from admin_access import service
from auth.db import get_session
from auth.dependencies import AuthUser, current_user
from auth.passwords import check_password_rules, hash_password, normalise_display_name, normalise_email
from errors import ApiError
from teacher_materials.models import Course, Topic, User
from text_validation import is_postgres_text

router = APIRouter(prefix="/api/admin", tags=["admin"])
admin_user = current_user(role="admin")


def invalid() -> ApiError:
    return ApiError(422, "validation_error", "Check the entered details and try again.")


class Body(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class AccountIn(Body):
    display_name: str
    email: str
    password: str
    role: Literal["student", "teacher", "admin"]


class StatusIn(Body):
    status: Literal["enabled", "disabled"]


class CourseIn(Body):
    title: str


async def raw_body(request: Request, _: AuthUser = Depends(admin_user)) -> bytes:
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > 16_384:
            raise invalid()
    return bytes(data)


def parse(model, raw: bytes):
    try:
        return model.model_validate_json(raw)
    except ValidationError:
        raise invalid() from None


def no_query(request: Request) -> None:
    if request.query_params:
        raise invalid()


def no_body(raw: bytes) -> None:
    if raw:
        raise invalid()


def positive(raw: str, maximum: int | None = None) -> int:
    if not raw.isascii() or not raw.isdecimal() or len(raw) > 10:
        raise invalid()
    value = int(raw)
    if value < 1 or (maximum is not None and value > maximum):
        raise invalid()
    return value


@router.get("/accounts")
def list_accounts(request: Request, _: AuthUser = Depends(admin_user), db: Session = Depends(get_session)):
    q = request.query_params
    allowed = {"search", "role", "status", "page", "page_size"}
    if any(key not in allowed or len(q.getlist(key)) != 1 for key in q):
        raise invalid()
    search = q.get("search", "").strip()
    role, status = q.get("role"), q.get("status", "enabled")
    if len(search) > 200 or not is_postgres_text(search) or role not in {None, "student", "teacher", "admin"} or status not in {"enabled", "disabled", "archived", "all"}:
        raise invalid()
    page, size = positive(q.get("page", "1")), positive(q.get("page_size", "20"), 100)
    filters = []
    if search:
        literal = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        filters.append(or_(User.display_name.ilike(f"%{literal}%", escape="\\"), User.email.ilike(f"%{literal}%", escape="\\")))
    if role:
        filters.append(User.role == role)
    if status != "all":
        filters.append(User.access_status == status)
    total = db.scalar(select(func.count()).select_from(User).where(*filters))
    users = db.scalars(select(User).where(*filters).order_by(func.lower(User.display_name), User.id).offset((page - 1) * size).limit(size)).all()
    return {"accounts": [service.account_json(user) for user in users], "total": total, "page": page, "page_size": size}


@router.post("/accounts", status_code=201)
def create_account(request: Request, raw: bytes = Depends(raw_body), _: AuthUser = Depends(admin_user), db: Session = Depends(get_session)):
    service.begin_change(db, request)
    no_query(request)
    body = parse(AccountIn, raw)
    try:
        name, email = normalise_display_name(body.display_name), normalise_email(body.email)
    except ValueError:
        raise invalid() from None
    if len(name) > 80 or check_password_rules(body.password, email):
        raise invalid()
    row = User(id=f"u-{uuid4().hex}", display_name=name, email=email, role=body.role,
               password_hash=hash_password(body.password), access_status="enabled")
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if getattr(exc.orig, "sqlstate", None) == "23505":
            raise ApiError(409, "email_exists", "An account with this email already exists.") from None
        raise
    return service.account_json(row)


@router.get("/accounts/{user_id}")
def get_account(user_id: str, request: Request, _: AuthUser = Depends(admin_user), db: Session = Depends(get_session)):
    no_query(request)
    return service.account_detail(db, service.get_account(db, user_id))


@router.put("/accounts/{user_id}/status")
def set_status(user_id: str, request: Request, raw: bytes = Depends(raw_body), _: AuthUser = Depends(admin_user), db: Session = Depends(get_session)):
    actor = service.begin_change(db, request)
    no_query(request)
    body = parse(StatusIn, raw)
    user = service.get_account(db, user_id)
    service.set_status(db, actor, user, body.status)
    return service.account_json(user)


@router.post("/accounts/{user_id}/archive")
def archive_account(user_id: str, request: Request, raw: bytes = Depends(raw_body), _: AuthUser = Depends(admin_user), db: Session = Depends(get_session)):
    actor = service.begin_change(db, request)
    no_query(request)
    no_body(raw)
    user = service.get_account(db, user_id)
    service.archive(db, actor, user)
    return service.account_json(user)


@router.put("/accounts/{user_id}/courses/{course_id}")
def grant_course(user_id: str, course_id: str, request: Request, raw: bytes = Depends(raw_body), _: AuthUser = Depends(admin_user), db: Session = Depends(get_session)):
    service.begin_change(db, request)
    no_query(request)
    no_body(raw)
    user = service.get_account(db, user_id)
    service.set_membership(db, user, course_id, True)
    return service.account_detail(db, user)


@router.delete("/accounts/{user_id}/courses/{course_id}")
def revoke_course(user_id: str, course_id: str, request: Request, raw: bytes = Depends(raw_body), _: AuthUser = Depends(admin_user), db: Session = Depends(get_session)):
    service.begin_change(db, request)
    no_query(request)
    no_body(raw)
    user = service.get_account(db, user_id)
    service.set_membership(db, user, course_id, False)
    return service.account_detail(db, user)


@router.get("/courses")
def list_courses(request: Request, _: AuthUser = Depends(admin_user), db: Session = Depends(get_session)):
    no_query(request)
    courses = db.scalars(select(Course).order_by(func.lower(Course.title), Course.id)).all()
    return {"courses": [service.course_json(course) for course in courses]}


@router.post("/courses", status_code=201)
def create_course(request: Request, raw: bytes = Depends(raw_body), _: AuthUser = Depends(admin_user), db: Session = Depends(get_session)):
    service.begin_change(db, request)
    no_query(request)
    body = parse(CourseIn, raw)
    title = body.title.strip()
    if not 1 <= len(title) <= 200 or not is_postgres_text(title):
        raise invalid()
    course = Course(id=uuid4(), title=title)
    db.add(course)
    db.flush()
    # A fresh course must be usable by existing publication forms, which
    # require a same-course topic. Both records commit or roll back together.
    db.add(Topic(id=uuid4(), course_id=course.id, name="General"))
    db.commit()
    return service.course_json(course)
