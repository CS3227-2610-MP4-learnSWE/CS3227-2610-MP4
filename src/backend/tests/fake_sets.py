"""Test fake for the STU-02-published-sets set provider (contract: workflow/specs/STU-02-published-sets/plan.md).

`FakeSetProvider` implements the `set_provider.SetProvider` protocol over in-memory `PracticeSet`
objects and a membership map. The old code fixture lives here as `FIXTURE_SET` (UUID id, questions
q1 to q3, choices a to c, key a, b, c). Install it with `install_fake(...)` (or the `fake_provider`
fixture in conftest.py); it overrides `set_provider.get_set_provider`.
"""
from __future__ import annotations

import copy
import threading
from dataclasses import dataclass
from datetime import datetime, timezone

from practice_data import PracticeSet, Question

FIXTURE_SET_ID = "a0000000-0000-4000-8000-000000000001"
UNKNOWN_SET_ID = "b0000000-0000-4000-8000-0000000000ff"  # a valid UUID that is no set
SE_BASICS_TOPIC_ID = "66666666-6666-4666-8666-666666666661"
FIXTURE_COURSE_ID = "11111111-1111-4111-8111-111111111111"
FIXTURE_COURSE_TITLE = "Software Engineering"
FIXTURE_TITLE = "Software engineering basics"
FIXTURE_TOPIC_NAME = "Software engineering basics"
CANONICAL = "0123456789abcdef-"

FIXTURE_SET = PracticeSet(
    FIXTURE_SET_ID,
    FIXTURE_TITLE,
    (
        Question(
            "q1", "What should a well-designed function have?", None,
            (("a", "A single, focused responsibility"), ("b", "As many responsibilities as possible"),
             ("c", "No descriptive name")),
            "a", "One focused responsibility makes a function easier to understand, test and change.",
            SE_BASICS_TOPIC_ID,
        ),
        Question(
            "q2", "Why do we keep automated tests alongside our code?", None,
            (("a", "To make the repository larger"), ("b", "To catch regressions when code changes"),
             ("c", "To avoid ever reviewing code")),
            "b", "Tests protect expected behaviour and can catch regressions introduced by later changes.",
            SE_BASICS_TOPIC_ID,
        ),
        Question(
            "q3", "What does this Python code print?", "values = [1, 2, 3]\nprint(len(values))",
            (("a", "2"), ("b", "4"), ("c", "3")),
            "c", "len returns the number of items. The list contains three items.",
            SE_BASICS_TOPIC_ID,
        ),
    ),
)


def is_canonical_uuid(value) -> bool:
    """Same defence as the real provider: only lowercase hyphenated UUID text resolves."""
    return (
        isinstance(value, str) and len(value) == 36 and all(c in CANONICAL for c in value)
        and [i for i, c in enumerate(value) if c == "-"] == [8, 13, 18, 23]
    )


@dataclass
class _Entry:
    practice_set: PracticeSet
    course_id: str
    course_title: str
    topic_name: str
    published_at: datetime


class FakeSetProvider:
    """In-memory SetProvider.

    members: None means every student sees every set; otherwise a dict student_id -> set of set ids.
    """

    def __init__(self, sets=None, members=None):
        self._lock = threading.RLock()
        self._entries: dict[str, _Entry] = {}
        self.members = members
        self.denied: set[tuple[str, str]] = set()
        self.calls: list[tuple] = []
        for s in sets if sets is not None else [FIXTURE_SET]:
            self.add(s)

    # ---- test controls
    def add(self, practice_set, *, course_id=FIXTURE_COURSE_ID, course_title=FIXTURE_COURSE_TITLE,
            topic_name=FIXTURE_TOPIC_NAME, published_at=None):
        with self._lock:
            self._entries[practice_set.id] = _Entry(
                practice_set, course_id, course_title, topic_name,
                published_at or datetime(2026, 1, 1, tzinfo=timezone.utc))

    def remove(self, set_id):
        with self._lock:
            self._entries.pop(set_id, None)

    def grant(self, student_id, set_id):
        with self._lock:
            self.denied.discard((str(student_id), set_id))
            if self.members is not None:
                self.members.setdefault(str(student_id), set()).add(set_id)

    def revoke(self, student_id, set_id):
        with self._lock:
            self.denied.add((str(student_id), set_id))
            if self.members is not None:
                self.members.setdefault(str(student_id), set()).discard(set_id)

    # ---- protocol
    def _visible(self, student_id, set_id):
        if set_id not in self._entries:
            return False
        if (str(student_id), set_id) in self.denied:
            return False
        if self.members is None:
            return True
        return set_id in self.members.get(str(student_id), set())

    def get_for_student(self, set_id, student_id):
        with self._lock:
            self.calls.append(("get_for_student", set_id, str(student_id)))
            if not is_canonical_uuid(set_id) and not (isinstance(set_id, str) and set_id in self._entries):
                return None
            if not self._visible(student_id, set_id):
                return None
            return copy.deepcopy(self._entries[set_id].practice_set)

    def get_many_for_student(self, student_id, set_ids):
        with self._lock:
            self.calls.append(("get_many_for_student", tuple(set_ids), str(student_id)))
            return {i: copy.deepcopy(self._entries[i].practice_set) for i in set_ids
                    if isinstance(i, str) and self._visible(student_id, i)}

    def _ordered(self, student_id):
        items = [e for i, e in self._entries.items() if self._visible(student_id, i)]
        return sorted(items, key=lambda e: (e.published_at, e.practice_set.id), reverse=True)

    def catalog_for_student(self, student_id, *, course_id=None, per_course_limit=None):
        from set_provider import CatalogCourse, CatalogSet

        with self._lock:
            self.calls.append(("catalog_for_student", str(student_id), course_id, per_course_limit))
            by_course: dict[str, list[_Entry]] = {}
            titles: dict[str, str] = {}
            for e in self._ordered(student_id):
                by_course.setdefault(e.course_id, []).append(e)
                titles[e.course_id] = e.course_title
            out = []
            for cid in sorted(by_course, key=lambda c: (titles[c].lower(), c)):
                if course_id is not None and cid != str(course_id):
                    continue
                entries = by_course[cid][:per_course_limit] if per_course_limit else by_course[cid]
                out.append(CatalogCourse(cid, titles[cid], tuple(
                    CatalogSet(e.practice_set.id, e.practice_set.title, e.practice_set.questions[0].topic_id,
                               e.topic_name, e.published_at, len(e.practice_set.questions))
                    for e in entries)))
            return out

    def accessible_sets(self, student_id):
        with self._lock:
            self.calls.append(("accessible_sets", str(student_id)))
            return [copy.deepcopy(e.practice_set) for e in self._ordered(student_id)][:200]


def install_fake(provider=None):
    """Override the provider dependency; returns the fake. Call `uninstall_fake()` afterwards."""
    import set_provider
    from main import app

    fake = provider or FakeSetProvider()
    app.dependency_overrides[set_provider.get_set_provider] = lambda: fake
    return fake


def uninstall_fake():
    import set_provider
    from main import app

    app.dependency_overrides.pop(set_provider.get_set_provider, None)
