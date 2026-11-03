"""Auth settings read from the environment on every call, so tests and deployments can change them."""
import os
from collections.abc import Mapping
from dataclasses import dataclass

from errors import ApiError

SAMESITE_VALUES = ("lax", "strict", "none")


def _int(env: Mapping[str, str], name: str, default: int) -> int:
    try:
        value = int((env.get(name) or "").strip())
    except ValueError:
        return default
    return value if value > 0 else default


@dataclass(frozen=True)
class AuthSettings:
    app_env: str
    database_url: str
    cookie_name: str
    cookie_secure: bool
    cookie_samesite: str
    session_ttl_seconds: int
    allowed_origins: tuple[str, ...]
    trust_proxy_headers: bool
    login_max_failures_per_email: int
    login_max_failures_per_ip: int
    login_window_seconds: int
    signup_max_per_ip: int
    signup_window_seconds: int

    @classmethod
    def load(cls, environ: Mapping[str, str] | None = None) -> "AuthSettings":
        env = os.environ if environ is None else environ
        listed = (o.strip() for o in (env.get("ALLOWED_ORIGINS") or "").split(","))
        return cls(
            app_env=(env.get("APP_ENV") or "").strip().lower(),
            database_url=(env.get("DATABASE_URL") or "").strip(),
            cookie_name=(env.get("SESSION_COOKIE_NAME") or "").strip() or "learnswe_session",
            # Anything but an explicit "false" keeps the cookie Secure (fail closed).
            cookie_secure=(env.get("SESSION_COOKIE_SECURE") or "true").strip().lower() != "false",
            cookie_samesite=(env.get("SESSION_COOKIE_SAMESITE") or "lax").strip().lower(),
            session_ttl_seconds=_int(env, "SESSION_TTL_SECONDS", 43200),
            allowed_origins=tuple(o for o in listed if o and o != "*"),
            trust_proxy_headers=(env.get("TRUST_PROXY_HEADERS") or "").strip().lower() == "true",
            login_max_failures_per_email=_int(env, "AUTH_LOGIN_MAX_FAILURES_PER_EMAIL", 5),
            login_max_failures_per_ip=_int(env, "AUTH_LOGIN_MAX_FAILURES_PER_IP", 20),
            login_window_seconds=_int(env, "AUTH_LOGIN_WINDOW_SECONDS", 900),
            signup_max_per_ip=_int(env, "AUTH_SIGNUP_MAX_PER_IP", 10),
            signup_window_seconds=_int(env, "AUTH_SIGNUP_WINDOW_SECONDS", 3600),
        )

    def validate(self) -> "AuthSettings":
        """Fail closed: 503 when cookie or database configuration is unusable. Returns self."""
        unsafe_cookie = self.app_env == "production" and not self.cookie_secure
        bad_samesite = self.cookie_samesite not in SAMESITE_VALUES
        none_insecure = self.cookie_samesite == "none" and not self.cookie_secure
        bad_database = not self.database_url.startswith("postgresql+psycopg://")
        if unsafe_cookie or bad_samesite or none_insecure or bad_database:
            raise ApiError(503, "service_unavailable", "The sign-in service is unavailable.")
        return self


def load_settings() -> AuthSettings:
    """Current settings, validated."""
    return AuthSettings.load().validate()
