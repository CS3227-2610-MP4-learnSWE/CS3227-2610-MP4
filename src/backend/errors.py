"""Shared API error type; rendered as {"detail": {"code", "message", ...}}."""


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, **extra: object) -> None:
        self.status = status
        self.code = code
        self.message = message
        self.extra = extra
