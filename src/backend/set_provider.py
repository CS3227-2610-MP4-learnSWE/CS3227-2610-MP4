"""The one place that reads published practice sets for students and decides which ones they can see."""
from collections import defaultdict
from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from auth.db import open_session
from practice_data import PracticeSet, Question
from study_lessons.progress import member_courses
from teacher_materials.models import CourseMembership, Topic
from teacher_publications.models import PublishedPracticeQuestion, PublishedPracticeSet

ACCESSIBLE_SETS_LIMIT = 200  # companion: newest sets per student
CATALOG_SETS_PER_COURSE = 100  # picker
GENERAL = "General"


def choice_id(index: int) -> str:
    return "abcd"[index]


@dataclass(frozen=True)
class CatalogSet:
    id: str
    title: str
    topic_id: str
    topic_name: str
    published_at: datetime
    question_count: int


@dataclass(frozen=True)
class CatalogCourse:
    id: str
    title: str
    sets: tuple[CatalogSet, ...]


class SetProvider(Protocol):
    def get_for_student(self, set_id: str, student_id: str) -> PracticeSet | None:
        """None for a non-canonical id, an unknown set, or a set in a course the student is not a member of."""
        ...

    def get_many_for_student(self, student_id: str, set_ids: Collection[str]) -> dict[str, PracticeSet]:
        """Only accessible sets; malformed ids are dropped without a query."""
        ...

    def catalog_for_student(
        self, student_id: str, *, course_id: UUID | None = None, per_course_limit: int | None = None
    ) -> list[CatalogCourse]:
        """Member courses (lower(title), id), each with its sets newest first."""
        ...

    def accessible_sets(self, student_id: str) -> list[PracticeSet]:
        """Accessible sets with questions, newest first, at most ACCESSIBLE_SETS_LIMIT."""
        ...


def _canonical_uuid(value: str) -> UUID | None:
    """The UUID for a canonical lowercase hyphenated string; None for anything else."""
    try:
        parsed = UUID(value)
    except (ValueError, TypeError, AttributeError):
        return None
    return parsed if str(parsed) == value else None


def _member_sets():
    """Published sets joined to the student's memberships: the single access rule."""
    return select(PublishedPracticeSet).join(
        CourseMembership, CourseMembership.course_id == PublishedPracticeSet.course_id
    )


def _newest_first(query):
    return query.order_by(PublishedPracticeSet.published_at.desc(), PublishedPracticeSet.id.desc())


def _build_sets(db: Session, rows: list[PublishedPracticeSet]) -> list[PracticeSet]:
    """Adapt published rows to the domain type, keeping the order of `rows`."""
    if not rows:
        return []
    by_set: dict[UUID, list[PublishedPracticeQuestion]] = defaultdict(list)
    query = (
        select(PublishedPracticeQuestion)
        .where(PublishedPracticeQuestion.set_id.in_([r.id for r in rows]))
        .order_by(PublishedPracticeQuestion.position)
    )
    for q in db.scalars(query):
        by_set[q.set_id].append(q)
    return [
        PracticeSet(
            id=str(row.id),
            title=row.title,
            questions=tuple(
                Question(
                    id=str(q.id),
                    text=q.question,
                    code=None,
                    choices=tuple((choice_id(i), text) for i, text in enumerate(q.choices)),
                    correct=choice_id(q.correct_choice_index),
                    explanation=q.explanation,
                    topic_id=str(row.topic_id),
                )
                for q in by_set[row.id]
            ),
        )
        for row in rows
    ]


class DbSetProvider:
    """Opens its own short session per call."""

    def get_for_student(self, set_id: str, student_id: str) -> PracticeSet | None:
        key = _canonical_uuid(set_id)
        if key is None:
            return None
        with open_session() as db:
            db.connection(execution_options={"isolation_level": "READ COMMITTED"})
            row = db.scalars(_member_sets().where(PublishedPracticeSet.id == key, CourseMembership.user_id == student_id)).one_or_none()
            return None if row is None else _build_sets(db, [row])[0]

    def get_many_for_student(self, student_id: str, set_ids: Collection[str]) -> dict[str, PracticeSet]:
        keys = {k for k in map(_canonical_uuid, set_ids) if k is not None}
        if not keys:
            return {}
        with open_session() as db:
            rows = list(db.scalars(_member_sets().where(PublishedPracticeSet.id.in_(keys), CourseMembership.user_id == student_id)))
            return {s.id: s for s in _build_sets(db, rows)}

    def catalog_for_student(
        self, student_id: str, *, course_id: UUID | None = None, per_course_limit: int | None = None
    ) -> list[CatalogCourse]:
        with open_session() as db:
            courses = [(cid, title) for cid, title in member_courses(db, student_id) if course_id in (None, cid)]
            if not courses:
                return []
            count = (
                select(func.count())
                .where(PublishedPracticeQuestion.set_id == PublishedPracticeSet.id)
                .scalar_subquery()
            )
            rank = func.row_number().over(
                partition_by=PublishedPracticeSet.course_id,
                order_by=(PublishedPracticeSet.published_at.desc(), PublishedPracticeSet.id.desc()),
            )
            ranked = (
                select(PublishedPracticeSet, Topic.name.label("topic_name"), count.label("n"), rank.label("rank"))
                .outerjoin(Topic, Topic.id == PublishedPracticeSet.topic_id)
                .where(PublishedPracticeSet.course_id.in_([cid for cid, _ in courses]))
                .subquery()
            )
            query = select(ranked)
            if per_course_limit is not None:
                query = query.where(ranked.c.rank <= per_course_limit)
            by_course: dict[UUID, list[CatalogSet]] = defaultdict(list)
            for row in db.execute(query.order_by(ranked.c.published_at.desc(), ranked.c.id.desc())):
                by_course[row.course_id].append(
                    CatalogSet(str(row.id), row.title, str(row.topic_id), row.topic_name or GENERAL, row.published_at, row.n)
                )
            return [CatalogCourse(str(cid), title, tuple(by_course[cid])) for cid, title in courses]

    def accessible_sets(self, student_id: str) -> list[PracticeSet]:
        with open_session() as db:
            query = _newest_first(_member_sets().where(CourseMembership.user_id == student_id)).limit(ACCESSIBLE_SETS_LIMIT)
            return _build_sets(db, list(db.scalars(query)))


provider: SetProvider = DbSetProvider()


def get_set_provider() -> SetProvider:
    """FastAPI dependency; tests override it."""
    return provider
