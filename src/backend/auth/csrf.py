"""CSRF defences for state-changing requests: Origin allow-list and per-session token."""
import hmac

from fastapi import Request

from auth.models import AuthSession
from auth.settings import AuthSettings
from errors import ApiError

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def _csrf_failed() -> ApiError:
    return ApiError(403, "csrf_failed", "The request could not be verified.")


def check_origin(request: Request, settings: AuthSettings) -> None:
    """A present Origin must be allow-listed or this server's own origin (unsafe methods only)."""
    origin = request.headers.get("origin")
    if request.method in SAFE_METHODS or origin is None:
        return
    own = f"{request.url.scheme}://{request.headers.get('host', '')}"
    if origin not in settings.allowed_origins and origin != own:
        raise _csrf_failed()


def check_csrf(request: Request, session: AuthSession) -> None:
    """Unsafe methods need X-CSRF-Token equal to the session's token."""
    if request.method in SAFE_METHODS:
        return
    sent = request.headers.get("x-csrf-token") or ""
    if not hmac.compare_digest(sent.encode("utf-8"), session.csrf_token.encode("utf-8")):
        raise _csrf_failed()
