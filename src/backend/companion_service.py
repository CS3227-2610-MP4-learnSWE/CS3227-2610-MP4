"""Companion logic: input checks, mode selection, history trimming and model message assembly.

The mode and the context come from stored data and server-side attempt state only. Nothing the
client sends (history, label, message) influences either.
"""
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

import companion_config as config
import companion_prompts as prompts
from attempt_store import Attempt
from companion_help import HELP_TEXT
from companion_schemas import HistoryItem
from errors import ApiError
from lesson_provider import LessonText
from llm_client import ChatMessage
from text_normalise import strip_format
from practice_data import KEY_VERSION, PracticeSet, Question

Mode = Literal["hint", "explain", "help", "lesson"]


@dataclass(frozen=True)
class Plan:
    mode: Mode
    questions: tuple[Question, ...]  # the questions placed in context (none for help)
    answers: dict[str, str] | None  # explain only: a snapshot of the student's choices
    # Questions checked for leaks but not placed in context (a pasted question from another set).
    leak_extra: tuple[Question, ...] = ()
    lessons: tuple[LessonText, ...] = ()  # lesson mode: the lessons placed in context


def validate_message(raw: str) -> str:
    message = raw.strip()
    if not message or len(message) > config.MESSAGE_MAX_CHARS:
        raise ApiError(422, "invalid_message", "The message must be 1 to 1,000 characters.")
    return message


def validate_history(items: Sequence[HistoryItem]) -> list[HistoryItem]:
    if (
        len(items) > config.HISTORY_MAX_ITEMS
        or any(len(i.text) > config.HISTORY_ITEM_MAX_CHARS for i in items)
        or any(i.role not in ("user", "assistant") for i in items)
    ):
        raise ApiError(422, "invalid_history", "The chat history is not valid.")
    return list(items)


def trim_history(items: Sequence[HistoryItem]) -> list[HistoryItem]:
    kept = list(items)[-config.HISTORY_KEEP_MESSAGES :]
    while kept and sum(len(i.text) for i in kept) > config.HISTORY_KEEP_CHARS:
        kept.pop(0)
    return kept


def select_mode(
    practice_set: PracticeSet | None,
    attempt: Attempt | None,
    student_attempts: Sequence[Attempt],
    match: Question | None,
    lessons: Sequence[LessonText] = (),
) -> Plan:
    """practice_set is None for page "other" and "lesson". attempt is the one named by the context, if any.

    lessons is the already-resolved list (the viewed lesson, or the related lessons). A match wins over it."""
    if practice_set is None:
        if match is None and lessons:
            return Plan("lesson", (), None, lessons=tuple(lessons))
        return Plan("hint", (match,), None) if match else Plan("help", (), None)
    # Read the status once: a submit racing this request cannot make it less restricted.
    explain = attempt is not None and attempt.status == "submitted"
    if explain:
        ids = [a.id for a in student_attempts]
        later = student_attempts[ids.index(attempt.id) + 1 :] if attempt.id in ids else []
        explain = not any(a.status == "in_progress" for a in later)
    if explain:
        if match is not None and match not in practice_set.questions:
            return Plan("hint", (match,), None)
        return Plan("explain", practice_set.questions, dict(attempt.answers))
    extra = (match,) if match is not None and match not in practice_set.questions else ()
    return Plan("hint", practice_set.questions, None, extra)


def _context_text(plan: Plan) -> str:
    if plan.mode == "help":
        return HELP_TEXT
    if plan.mode == "lesson":
        return "\n\n".join(
            f"{prompts.LESSON_OPEN}\nLesson \"{_safe(l.title)}\":\n"
            f"{_safe(l.content[: config.LESSON_MAX_CHARS])}\n{prompts.LESSON_CLOSE}"
            for l in plan.lessons
        )
    lines: list[str] = []
    for n, q in enumerate(plan.questions, 1):
        lines.append(f"Question {n}: {q.text}")
        if q.code:
            lines.append(f"Code:\n{q.code}")
        if plan.mode == "explain":
            answers = plan.answers or {}
            lines.append("Choices: " + "; ".join(f"{cid}) {t}" for cid, t in q.choices))
            lines.append(f"Student's choice: {answers.get(q.id, 'none')}")
            lines.append(f"Correct choice: {q.correct}")
            lines.append(f"Explanation: {q.explanation}")
        lines.append("")
    if plan.mode == "explain":
        lines.append(f"Answer key version: {KEY_VERSION}")
    return "\n".join(lines).strip()


_WRAP = r"[*_`~]*"
_MARKER_RE = re.compile(
    _WRAP + r"not\s*_\s*in\s*_\s*lesson" + _WRAP + r"\s*:" + _WRAP, re.IGNORECASE
)


def _safe(text: str) -> str:
    """Stop lesson text from closing or faking the delimited data block."""
    for delimiter in (prompts.LESSON_OPEN, prompts.LESSON_CLOSE):
        text = re.sub(re.escape(delimiter.split(" (")[0]), "[removed]", text, flags=re.IGNORECASE)
    return text


def finish_lesson_reply(text: str, lessons: Sequence[LessonText]) -> tuple[str, list[LessonText]]:
    """Apply the NOT_IN_LESSON marker: a leading marker gives the limitation sentence and no sources.

    Text is matched after NFKC and format-character removal (full-width spellings count), ignoring
    case, spacing and markdown wrapping. Every marker is removed; it never reaches the student."""
    normal = strip_format(text).strip()
    leading = _MARKER_RE.match(normal) is not None
    rest = _MARKER_RE.sub("", normal).strip()
    if leading:
        return f"{config.LIMITATION_SENTENCE} {rest}".strip(), []
    return rest, list(lessons)


def build_messages(
    plan: Plan, message: str, history: Sequence[HistoryItem], label: str | None
) -> list[ChatMessage]:
    heading = prompts.CONTEXT_HEADINGS[plan.mode]
    messages = [
        ChatMessage("system", prompts.RULES[plan.mode]),
        ChatMessage("system", f"{heading}\n{_context_text(plan)}"),
    ]
    for item in trim_history(history):
        role: Literal["user", "assistant"] = "assistant" if item.role == "assistant" else "user"
        messages.append(ChatMessage(role, item.text))
    block = [prompts.UNTRUSTED_OPEN]
    if label and label.strip():
        block.append(f"Page label (untrusted): {label.strip()}")
    block += [f"Student message: {message}", prompts.UNTRUSTED_CLOSE]
    messages.append(ChatMessage("user", "\n".join(block)))
    return messages
