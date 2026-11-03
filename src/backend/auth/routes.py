"""Auth endpoints: signup, login, logout, me, and the reference course-access route."""
from datetime import timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from auth import rate_limit
from auth.csrf import check_csrf, check_origin
from auth.db import get_session
from auth.dependencies import AuthUser, SessionContext, current_user, require_course_member, session_context
from auth.passwords import (
    EMAIL_MAX,
    PASSWORD_MAX,
    check_password_rules,
    clean_email,
    hash_password,
    normalise_display_name,
    normalise_email,
    verify_password,
)
from auth.sessions import create_session, load_session, revoke_session
from auth.settings import AuthSettings, load_settings
from errors import ApiError
from teacher_materials.models import Course, User

router = APIRouter(prefix="/api", tags=["auth"])

LOGIN_PASSWORD_MAX = 1024


class _Body(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class SignupIn(_Body):
    display_name: str
    email: str
    password: str


class LoginIn(_Body):
    email: str
    password: str


def guard(request: Request) -> AuthSettings:
    """Config check (503), then Origin check (403), before anything else runs."""
    settings = load_settings()
    check_origin(request, settings)
    return settings


async def raw_body(request: Request, _: AuthSettings = Depends(guard)) -> bytes:
    return await request.body()


def _validation_error(fields: list[str]) -> ApiError:
    return ApiError(422, "validation_error", "Some fields are invalid.", fields=sorted(set(fields)))


def _parse[T: _Body](model: type[T], raw: bytes) -> T:
    """Strict parse. Offending field names only, never values."""
    try:
        return model.model_validate_json(raw)
    except ValidationError as exc:
        raise _validation_error([str(e["loc"][0]) for e in exc.errors() if e["loc"]]) from None


def client_ip(request: Request, settings: AuthSettings) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if settings.trust_proxy_headers and forwarded.strip():
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def _set_cookie_args(settings: AuthSettings) -> dict:
    return {
        "key": settings.cookie_name,
        "path": "/",
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite.capitalize(),
    }


def _timestamp(value) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@router.post("/auth/signup", status_code=202)
def signup(request: Request, raw: bytes = Depends(raw_body), db: Session = Depends(get_session)) -> dict[str, str]:
    settings = load_settings()
    body = _parse(SignupIn, raw)
    bad = []
    try:
        name = normalise_display_name(body.display_name)
    except ValueError:
        bad.append("display_name")
    try:
        email = normalise_email(body.email)
    except ValueError:
        bad.append("email")
        email = clean_email(body.email)
    if check_password_rules(body.password, email):
        bad.append("password")
    if bad:
        raise _validation_error(bad)
    wait = rate_limit.admit(f"signup:ip:{client_ip(request, settings)}", settings.signup_max_per_ip, settings.signup_window_seconds)
    if wait is not None:
        raise rate_limit.limited(wait)
    # One hash on every path; the unique email index makes a duplicate a silent no-op, also under races.
    password_hash = hash_password(body.password)
    db.execute(
        pg_insert(User)
        .values(id=f"u-{uuid4().hex}", display_name=name, role="student", email=email, password_hash=password_hash)
        .on_conflict_do_nothing(index_elements=["email"])
    )
    db.commit()
    return {"status": "accepted"}


@router.post("/auth/login")
def login(request: Request, raw: bytes = Depends(raw_body), db: Session = Depends(get_session)) -> JSONResponse:
    settings = load_settings()
    body = _parse(LoginIn, raw)
    email = clean_email(body.email)
    bad = []
    if not 1 <= len(email) <= EMAIL_MAX:
        bad.append("email")
    if not 1 <= len(body.password) <= LOGIN_PASSWORD_MAX:
        bad.append("password")
    if bad:
        raise _validation_error(bad)
    window = settings.login_window_seconds
    keys = [
        (f"login:ip:{client_ip(request, settings)}", settings.login_max_failures_per_ip, window),
        (f"login:email:{email}", settings.login_max_failures_per_email, window),
    ]
    wait = rate_limit.reserve(keys)
    if wait is not None:
        raise rate_limit.limited(wait)
    failed = True
    try:
        user = db.scalar(select(User).where(User.email == email))
        failed = not verify_password(body.password, user.password_hash if user else None) or user is None
    finally:
        rate_limit.settle(keys, failed)
    if failed:
        raise ApiError(401, "invalid_credentials", "Email or password is incorrect.")
    token, session_row = create_session(db, user, settings.session_ttl_seconds)
    response = JSONResponse({"user": AuthUser.from_row(user).as_json(), "csrf_token": session_row.csrf_token})
    response.set_cookie(value=token, max_age=settings.session_ttl_seconds, **_set_cookie_args(settings))
    return response


@router.post("/auth/logout")
def logout(request: Request, settings: AuthSettings = Depends(guard), db: Session = Depends(get_session)) -> JSONResponse:
    token = request.cookies.get(settings.cookie_name)
    found = load_session(db, token) if token else None
    if found is not None:
        check_csrf(request, found[0])
        revoke_session(db, token)
    response = JSONResponse({"status": "ok"})
    response.delete_cookie(**_set_cookie_args(settings))
    return response


@router.get("/auth/me")
def me(context: SessionContext = Depends(session_context)) -> dict:
    return {"user": context.user.as_json(), "csrf_token": context.csrf_token}


@router.get("/courses/{course_id}")
def read_course(course_id: str, user: AuthUser = Depends(current_user()), db: Session = Depends(get_session)) -> dict[str, str]:
    try:
        wanted = UUID(course_id)
    except ValueError:
        raise ApiError(422, "validation_error", "A valid course id is required.", fields=["course_id"]) from None
    course: Course = require_course_member(db, user, wanted)
    return {"id": str(course.id), "title": course.title, "created_at": _timestamp(course.created_at)}


async def add_no_store(request: Request, call_next):
    """Middleware: auth responses must never be cached."""
    response = await call_next(request)
    if request.url.path.startswith("/api/auth/"):
        response.headers["Cache-Control"] = "no-store"
    return response
