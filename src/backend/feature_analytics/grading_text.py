"""Text handed to the grader: caps, redaction and formatting. No identity or answer-key data can pass through here."""
import re
from collections.abc import Sequence
from dataclasses import dataclass

from feature_analytics import config

_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]{1,64}@[A-Za-z0-9\-]{1,63}(?:\.[A-Za-z0-9\-]{1,63})*\.[A-Za-z]{2,24}")
_LONG_TOKEN = re.compile(r"[A-Za-z0-9_\-]{32,}")
REDACTED = "[redacted]"


@dataclass(frozen=True)
class GradingContent:
    request_text: str
    response_text: str
    context_text: str | None = None


def redact(text: str) -> str:
    """Replace email addresses and any run of 32 or more token characters with [redacted]."""
    return _LONG_TOKEN.sub(REDACTED, _EMAIL.sub(REDACTED, text))


def _cap(text: str | None, limit: int) -> str | None:
    if text is None:
        return None
    return text.replace("\x00", "")[:limit]


def truncate_for_storage(content: GradingContent) -> GradingContent:
    """Cap the three fields at REQUEST_MAX_CHARS, RESPONSE_MAX_CHARS and CONTEXT_MAX_CHARS characters."""
    return GradingContent(
        _cap(content.request_text, config.REQUEST_MAX_CHARS) or "",
        _cap(content.response_text, config.RESPONSE_MAX_CHARS) or "",
        _cap(content.context_text, config.CONTEXT_MAX_CHARS),
    )


def prepare_for_storage(content: GradingContent) -> GradingContent:
    """Truncate, redact, then truncate again (redacting a short address makes it longer, so the cap must hold last)."""
    capped = truncate_for_storage(content)
    redacted = GradingContent(
        redact(capped.request_text), redact(capped.response_text),
        None if capped.context_text is None else redact(capped.context_text),
    )
    return truncate_for_storage(redacted)


def format_mcq_batch_for_grading(questions: Sequence[tuple[str, Sequence[str]]]) -> str:
    """Plain text of (stem, choices) pairs only. There is deliberately no parameter for a correct choice or explanation."""
    lines: list[str] = []
    for number, (stem, choices) in enumerate(questions, 1):
        lines.append(f"Q{number}: {stem}")
        lines.extend(f" {chr(ord('A') + index)}) {choice}" for index, choice in enumerate(choices))
    return "\n".join(lines)
