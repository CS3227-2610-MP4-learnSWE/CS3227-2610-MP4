"""Attempt store: the interface and its PostgreSQL implementation (table `practice_attempt`)."""
import re
import secrets
from collections.abc import Collection, Iterator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from sqlalchemy import func, or_, select, update

from attempt_models import PracticeAttempt
from auth.db import open_session
from errors import ApiError


@dataclass
class Attempt:
    id: str
    student_id: str
    set_id: str
    status: str = "in_progress"
    answers: dict[str, str] = field(default_factory=dict)
    score_correct: int | None = None
    score_total: int | None = None
    key_version: str | None = None
    correct_question_ids: list[str] = field(default_factory=list)
    submitted_at: datetime | None = None


@dataclass(frozen=True)
class SetSummary:
    set_id: str
    attempts_submitted: int
    best_correct: int
    best_total: int
    latest: Attempt


@dataclass(frozen=True)
class PeriodAttempts:
    set_id: str
    student_id: str
    submitted_count: int
    latest: Attempt


class AttemptStore(Protocol):
    def create(self, student_id: str, set_id: str) -> Attempt: ...

    def get_owned(self, attempt_id: str, student_id: str) -> Attempt | None:
        """Return the attempt only if it exists and belongs to the student."""
        ...

    def list_for_student(self, student_id: str, set_id: str) -> list[Attempt]:
        """The student's attempts on one set, oldest first (creation order)."""
        ...

    def lock(self, attempt_id: str) -> AbstractContextManager[Attempt]:
        """Yield a freshly read, row-locked attempt; changes are saved on a clean exit, rolled back on error."""
        ...

    def submitted_summaries(self, student_id: str) -> list[SetSummary]:
        """Per set with a submitted attempt: count, best and latest submitted attempt. Ordered by set id."""
        ...


def _to_attempt(row: PracticeAttempt) -> Attempt:
    return Attempt(
        id=row.id,
        student_id=row.student_id,
        set_id=row.set_id,
        status=row.status,
        answers=dict(row.answers),
        score_correct=row.score_correct,
        score_total=row.score_total,
        key_version=row.key_version,
        correct_question_ids=list(row.correct_question_ids),
        submitted_at=row.submitted_at,
    )


_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,64}")


def _valid_id(attempt_id: str) -> bool:
    """Ids we issue are urlsafe tokens; anything else cannot exist, so no query is made."""
    return _ID_PATTERN.fullmatch(attempt_id) is not None


class DbAttemptStore:
    def create(self, student_id: str, set_id: str) -> Attempt:
        row = PracticeAttempt(
            id=secrets.token_urlsafe(16), student_id=student_id, set_id=set_id,
            status="in_progress", answers={}, correct_question_ids=[],
        )
        with open_session() as db:
            db.add(row)
            db.commit()
            return _to_attempt(row)

    def get_owned(self, attempt_id: str, student_id: str) -> Attempt | None:
        if not _valid_id(attempt_id):
            return None
        with open_session() as db:
            row = db.scalars(
                select(PracticeAttempt).where(PracticeAttempt.id == attempt_id, PracticeAttempt.student_id == student_id)
            ).one_or_none()
            return None if row is None else _to_attempt(row)

    def list_for_student(self, student_id: str, set_id: str) -> list[Attempt]:
        with open_session() as db:
            rows = db.scalars(
                select(PracticeAttempt)
                .where(PracticeAttempt.student_id == student_id, PracticeAttempt.set_id == set_id)
                .order_by(PracticeAttempt.seq)
            )
            return [_to_attempt(r) for r in rows]

    @contextmanager
    def lock(self, attempt_id: str) -> Iterator[Attempt]:
        if not _valid_id(attempt_id):
            raise ApiError(404, "attempt_not_found", "Attempt not found.")
        with open_session() as db:
            row = db.scalars(
                select(PracticeAttempt).where(PracticeAttempt.id == attempt_id).with_for_update()
            ).one_or_none()
            if row is None:
                raise ApiError(404, "attempt_not_found", "Attempt not found.")
            attempt = _to_attempt(row)
            was_submitted = row.status == "submitted"
            try:
                yield attempt
                if not was_submitted:
                    values = {
                        "answers": attempt.answers,
                        "status": attempt.status,
                        "score_correct": attempt.score_correct,
                        "score_total": attempt.score_total,
                        "key_version": attempt.key_version,
                        "correct_question_ids": attempt.correct_question_ids,
                    }
                    if attempt.status == "submitted":
                        values["submitted_at"] = func.clock_timestamp()
                    db.execute(update(PracticeAttempt).where(PracticeAttempt.id == attempt_id).values(**values))
                    db.flush()
                    db.refresh(row)
                    attempt.submitted_at = row.submitted_at
                db.commit()
            except BaseException:
                db.rollback()
                raise

    def submitted_summaries(self, student_id: str) -> list[SetSummary]:
        best_rank = func.row_number().over(
            partition_by=PracticeAttempt.set_id,
            order_by=((PracticeAttempt.score_correct * 1.0 / PracticeAttempt.score_total).desc(), PracticeAttempt.seq),
        )
        latest_rank = func.row_number().over(
            partition_by=PracticeAttempt.set_id,
            order_by=(PracticeAttempt.submitted_at.desc(), PracticeAttempt.seq.desc()),
        )
        count = func.count().over(partition_by=PracticeAttempt.set_id)
        ranked = (
            select(
                PracticeAttempt.id.label("id"),
                best_rank.label("best_rank"),
                latest_rank.label("latest_rank"),
                count.label("n"),
            )
            .where(PracticeAttempt.student_id == student_id, PracticeAttempt.status == "submitted")
            .subquery()
        )
        query = (
            select(PracticeAttempt, ranked.c.best_rank, ranked.c.latest_rank, ranked.c.n)
            .join(ranked, ranked.c.id == PracticeAttempt.id)
            .where(or_(ranked.c.best_rank == 1, ranked.c.latest_rank == 1))
            .order_by(PracticeAttempt.set_id)
        )
        best: dict[str, PracticeAttempt] = {}
        latest: dict[str, PracticeAttempt] = {}
        counts: dict[str, int] = {}
        with open_session() as db:
            for row, best_n, latest_n, n in db.execute(query):
                counts[row.set_id] = n
                if best_n == 1:
                    best[row.set_id] = row
                if latest_n == 1:
                    latest[row.set_id] = row
            return [
                SetSummary(sid, counts[sid], best[sid].score_correct, best[sid].score_total, _to_attempt(latest[sid]))
                for sid in sorted(counts)
            ]


def submitted_in_period(
    set_ids: Collection[str], student_ids: Collection[str], start: datetime | None, end: datetime
) -> list[PeriodAttempts]:
    """Per (set, student) with a submitted attempt in [start, end): the count and the latest by (submitted_at, seq)."""
    if not set_ids or not student_ids:
        return []
    query = (
        select(PracticeAttempt)
        .where(
            PracticeAttempt.set_id.in_(list(set_ids)),
            PracticeAttempt.student_id.in_(list(student_ids)),
            PracticeAttempt.status == "submitted",
            PracticeAttempt.submitted_at < end,
        )
        .order_by(PracticeAttempt.submitted_at, PracticeAttempt.seq)
    )
    if start is not None:
        query = query.where(PracticeAttempt.submitted_at >= start)
    counts: dict[tuple[str, str], int] = {}
    latest: dict[tuple[str, str], PracticeAttempt] = {}
    with open_session() as db:
        for row in db.scalars(query):
            key = (row.set_id, row.student_id)
            counts[key] = counts.get(key, 0) + 1
            latest[key] = row
        return [PeriodAttempts(key[0], key[1], counts[key], _to_attempt(latest[key])) for key in sorted(counts)]


store: AttemptStore = DbAttemptStore()
