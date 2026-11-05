"""The one error type the CLI turns into `error:` lines and an exit code."""

from __future__ import annotations


class TrackerError(Exception):
    """A usage or input problem. `message` has no `error: ` prefix and may hold several lines."""

    def __init__(self, message: str, exit_code: int = 2):
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code
