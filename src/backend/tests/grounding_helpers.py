"""Shared helpers for the STU-03-grounding tests (contract: workflow/specs/STU-03-grounding/plan.md).

`FakeLessonProvider` implements the `lesson_provider.LessonProvider` protocol in memory and records
every call, so route tests run with a fake LLM and no lesson rows. Tests that need the real
`published_lesson` / `course_membership` rules use the DB helpers in stu01_helpers.py instead.
Install with `install_lessons(...)` (or the `fake_lessons` fixture in conftest.py).
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass

from companion_helpers import body_of  # noqa: F401  (re-exported for convenience)

LESSON_PAGE = "lesson"
MARKER = "NOT_IN_LESSON:"
LIMITATION = "This isn't covered in the lesson materials I can see, so this is general help, not course material."
LESSON_CANNED = "I can't share or confirm practice answers. Ask me about the idea in the lesson and I will explain it."
LESSON_NOT_FOUND_BODY = {"detail": {"code": "lesson_not_found", "message": "Lesson not found."}}
BEGIN = "BEGIN LESSON TEXT"
END = "END LESSON TEXT"


@dataclass
class _Row:
    id: str
    title: str
    content: str
    course: str
    order: int
    withdrawn: bool = False


class FakeLessonProvider:
    """In-memory LessonProvider.

    members: None means every student is a member of every course; otherwise a dict
    student_id -> set of course names.
    """

    def __init__(self, members=None):
        self._lock = threading.RLock()
        self._rows: dict[str, _Row] = {}
        self._counter = 0
        self.members = members
        self.calls: list[tuple] = []

    # ---- test controls
    def add(self, title, content, *, course="c1", withdrawn=False, lesson_id=None) -> str:
        """Add a lesson; later additions are newer. Returns the canonical id."""
        with self._lock:
            self._counter += 1
            lid = lesson_id or str(uuid.uuid4())
            self._rows[lid] = _Row(lid, title, content, course, self._counter, withdrawn)
            return lid

    def withdraw(self, lesson_id):
        with self._lock:
            self._rows[lesson_id].withdrawn = True

    def revoke(self, student_id, course="c1"):
        with self._lock:
            if self.members is None:
                self.members = {}
            self.members.setdefault(str(student_id), set()).discard(course)

    def grant(self, student_id, course="c1"):
        with self._lock:
            if self.members is None:
                self.members = {}
            self.members.setdefault(str(student_id), set()).add(course)

    def count(self, name) -> int:
        return len([c for c in self.calls if c[0] == name])

    # ---- protocol
    def _visible(self, user_id, row) -> bool:
        if row.withdrawn:
            return False
        if self.members is None:
            return True
        return row.course in self.members.get(str(user_id), set())

    def get_visible(self, lesson_id, user):
        from lesson_provider import LessonText

        with self._lock:
            self.calls.append(("get_visible", lesson_id, str(user.id)))
            try:
                key = str(uuid.UUID(str(lesson_id)))
            except (ValueError, AttributeError, TypeError):
                return None
            row = self._rows.get(key)
            if row is None or not self._visible(user.id, row):
                return None
            return LessonText(row.id, row.title, row.content)

    def find_related(self, message, user, limit=2):
        import lesson_match
        from lesson_provider import LessonText

        with self._lock:
            self.calls.append(("find_related", message, str(user.id)))
            visible = sorted((r for r in self._rows.values() if self._visible(user.id, r)),
                             key=lambda r: r.order, reverse=True)  # newest first, as the real provider
            texts = [LessonText(r.id, r.title, r.content) for r in visible]
        return lesson_match.select_related(message, texts, limit)


def install_lessons(provider=None) -> FakeLessonProvider:
    """Override the lesson provider dependency; call `uninstall_lessons()` afterwards."""
    import lesson_provider
    from main import app

    fake = provider or FakeLessonProvider()
    app.dependency_overrides[lesson_provider.get_lesson_provider] = lambda: fake
    return fake


def uninstall_lessons() -> None:
    import lesson_provider
    from main import app

    app.dependency_overrides.pop(lesson_provider.get_lesson_provider, None)


def lesson_ask(student, message, lesson_id, **kw):
    """POST a message from a lesson page."""
    from companion_helpers import ask

    return ask(student, message, page=LESSON_PAGE, context_extra={"lesson_id": lesson_id}, **kw)


def other_ask(student, message, **kw):
    from companion_helpers import ask

    return ask(student, message, page="other", **kw)


def between_markers(text: str) -> str:
    """The text between the first BEGIN LESSON TEXT and END LESSON TEXT delimiters ('' if absent)."""
    a = text.find(BEGIN)
    if a < 0:
        return ""
    b = text.find(END, a)
    return text[a + len(BEGIN):b if b >= 0 else len(text)]
