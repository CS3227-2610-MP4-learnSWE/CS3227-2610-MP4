"""The one place the companion reads published lessons for a student (own short session per call)."""
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

import companion_config as config
from auth.db import open_session
from auth.dependencies import AuthUser
from errors import ApiError
from lesson_match import select_related
from study_lessons.access import get_visible_lesson, visible_lessons
from study_lessons.models import PublishedLesson


@dataclass(frozen=True)
class LessonText:
    id: str  # canonical lowercase hyphenated UUID
    title: str
    content: str  # at most LESSON_MAX_CHARS


class LessonProvider(Protocol):
    def get_visible(self, lesson_id: str, user: AuthUser) -> LessonText | None:
        """None for a malformed id, an unknown, draft or withdrawn lesson, or a course the user is not a member of."""
        ...

    def find_related(
        self, message: str, user: AuthUser, limit: int = config.RELATED_LESSON_LIMIT
    ) -> list[LessonText]:
        """Visible lessons related to the message by word overlap, best first; [] when none qualify."""
        ...


def _to_text(row: PublishedLesson) -> LessonText:
    return LessonText(str(row.id), row.title, row.content[: config.LESSON_MAX_CHARS])


class DbLessonProvider:
    def get_visible(self, lesson_id: str, user: AuthUser) -> LessonText | None:
        try:
            key = UUID(lesson_id)
        except (ValueError, TypeError, AttributeError):
            return None
        with open_session() as db:
            try:
                return _to_text(get_visible_lesson(db, user, key))
            except ApiError:
                return None

    def find_related(
        self, message: str, user: AuthUser, limit: int = config.RELATED_LESSON_LIMIT
    ) -> list[LessonText]:
        with open_session() as db:
            query = (
                visible_lessons(user)
                .order_by(PublishedLesson.published_at.desc(), PublishedLesson.id.desc())
                .limit(config.LESSON_CANDIDATES)
            )
            candidates = [_to_text(row) for row in db.scalars(query)]
        return select_related(message, candidates, limit)


provider: LessonProvider = DbLessonProvider()


def get_lesson_provider() -> LessonProvider:
    """FastAPI dependency; tests override it."""
    return provider
