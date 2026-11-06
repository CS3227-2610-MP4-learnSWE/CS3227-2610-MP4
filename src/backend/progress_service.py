"""Builds the progress view from lesson helpers, attempt summaries and topic names."""
from collections.abc import Mapping
from fractions import Fraction
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from attempt_store import AttemptStore, SetSummary, store
from practice_data import PRACTICE_SETS, PracticeSet
from progress_rules import (
    MIN_ANSWERS_FOR_TOPIC,
    RECENT_LESSON_LIMIT,
    WEAK_BELOW_PERCENT,
    accuracy_percent,
    topic_status,
)
from progress_schemas import (
    CourseProgress,
    LatestScore,
    LessonProgress,
    LessonTotals,
    PracticeProgress,
    ProgressOut,
    RecentLesson,
    ScoreCount,
    SetProgress,
    TopicItem,
    TopicProgress,
    TopicRef,
    TopicRule,
)
from study_lessons.progress import CourseCounts, completed_lessons, completion_counts, member_courses
from teacher_materials.models import Topic
from timestamps import utc_timestamp

GENERAL = "General"
_STATUS_ORDER = {"needs_practice": 0, "on_track": 1, "insufficient": 2}

Tally = dict[UUID | None, list[int]]  # topic id (None = no topic) -> [answered, correct]


def _lessons(db: Session, student_id: str) -> LessonProgress:
    counts = completion_counts(db, student_id)
    courses = []
    for cid, title in member_courses(db, student_id):
        c = counts.get(cid, CourseCounts(0, 0))
        courses.append(CourseProgress(id=str(cid), title=title, lesson_count=c.lesson_count, completed_count=c.completed_count))
    totals = LessonTotals(
        lesson_count=sum(c.lesson_count for c in courses), completed_count=sum(c.completed_count for c in courses)
    )
    recent = [
        RecentLesson(
            lesson_id=str(r.lesson_id), course_id=str(r.course_id), title=r.title, completed_at=utc_timestamp(r.completed_at)
        )
        for r in completed_lessons(db, student_id)[:RECENT_LESSON_LIMIT]
    ]
    return LessonProgress(totals=totals, courses=courses, recent=recent)


def _set_progress(summary: SetSummary, practice_set: PracticeSet) -> SetProgress:
    latest = summary.latest
    return SetProgress(
        set_id=summary.set_id,
        title=practice_set.title,
        attempts_submitted=summary.attempts_submitted,
        best=ScoreCount(correct=summary.best_correct, total=summary.best_total),
        latest=LatestScore(
            correct=latest.score_correct, total=latest.score_total, submitted_at=utc_timestamp(latest.submitted_at)
        ),
    )


def _average_latest_percent(sets: list[SetProgress]) -> int | None:
    """Floor of the mean latest percentage, in exact rational arithmetic."""
    if not sets:
        return None
    mean = sum(Fraction(s.latest.correct * 100, s.latest.total) for s in sets) / len(sets)
    return mean.numerator // mean.denominator


def _parse_uuid(value: str | None) -> UUID | None:
    try:
        return None if value is None else UUID(value)
    except ValueError:
        return None


def _tally_topics(summary: SetSummary, practice_set: PracticeSet, tally: Tally) -> None:
    latest = summary.latest
    for question in practice_set.questions:
        if question.id not in latest.answers:
            continue
        counts = tally.setdefault(_parse_uuid(question.topic_id), [0, 0])
        counts[0] += 1
        counts[1] += question.id in latest.correct_question_ids


def _topic_items(db: Session, tally: Tally) -> list[TopicItem]:
    wanted = {t for t in tally if t is not None}
    names = dict(db.execute(select(Topic.id, Topic.name).where(Topic.id.in_(wanted))).all()) if wanted else {}
    merged: Tally = {}
    for topic, (answered, correct) in tally.items():
        bucket = merged.setdefault(topic if topic in names else None, [0, 0])
        bucket[0] += answered
        bucket[1] += correct
    items = [
        TopicItem(
            topic=TopicRef(id=None if t is None else str(t), name=GENERAL if t is None else names[t]),
            answered=answered,
            correct=correct,
            accuracy_percent=accuracy_percent(answered, correct),
            status=topic_status(answered, correct),
        )
        for t, (answered, correct) in merged.items()
    ]
    items.sort(
        key=lambda i: (_STATUS_ORDER[i.status], i.accuracy_percent, i.topic.name.lower(), i.topic.id is None, i.topic.id or "")
    )
    return items


def build_progress(
    db: Session,
    student_id: str,
    attempts: AttemptStore = store,
    sets: Mapping[str, PracticeSet] = PRACTICE_SETS,
) -> ProgressOut:
    lessons = _lessons(db, student_id)
    tally: Tally = {}
    progress_sets = []
    for summary in attempts.submitted_summaries(student_id):
        practice_set = sets.get(summary.set_id)
        if practice_set is None:
            continue
        progress_sets.append(_set_progress(summary, practice_set))
        _tally_topics(summary, practice_set, tally)
    progress_sets.sort(key=lambda s: (s.title.lower(), s.set_id))
    return ProgressOut(
        lessons=lessons,
        practice=PracticeProgress(sets=progress_sets, average_latest_percent=_average_latest_percent(progress_sets)),
        topics=TopicProgress(
            rule=TopicRule(min_answers=MIN_ANSWERS_FOR_TOPIC, weak_below_percent=WEAK_BELOW_PERCENT),
            items=_topic_items(db, tally),
        ),
    )
