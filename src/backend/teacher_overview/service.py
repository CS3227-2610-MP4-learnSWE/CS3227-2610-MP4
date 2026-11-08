"""Build the teacher learning overview. Read-only; one student roster per course bounds every count."""
from collections import defaultdict
from datetime import datetime, timezone
from fractions import Fraction
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from attempt_store import Attempt, PeriodAttempts, submitted_in_period
from progress_rules import accuracy_percent
from study_lessons.progress import course_student_ids, lesson_completion_stats, member_courses
from teacher_materials.models import Topic
from teacher_overview.schemas import ReportingPeriod, period_json
from teacher_publications.models import PublishedPracticeQuestion, PublishedPracticeSet
from timestamps import utc_timestamp

TOP_MISSED = 5
GENERAL_TOPIC = "General"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _rate(part: int, whole: int) -> int | None:
    """Whole-percent rate rounded down; None when there is nothing to divide by."""
    return accuracy_percent(whole, part) if whole else None


def _missed_questions(sets: list[dict], questions: dict[str, list[tuple[str, int, str]]], latest: dict[str, list[Attempt]]) -> list[dict]:
    """The most missed questions over the latest attempts, ranked by exact miss fraction, misses, set title, position, set id."""
    found = []
    for item in sets:
        attempts = latest.get(item["set_id"], [])
        for question_id, position, text in questions.get(item["set_id"], []):
            answered = [a for a in attempts if question_id in a.answers]
            missed = sum(question_id not in a.correct_question_ids for a in answered)
            if missed:
                found.append({
                    "set_id": item["set_id"], "set_title": item["title"], "position": position, "question": text,
                    "missed": missed, "answered": len(answered), "miss_rate_percent": _rate(missed, len(answered)),
                })
    found.sort(key=lambda m: (-Fraction(m["missed"], m["answered"]), -m["missed"], m["set_title"].lower(), m["position"], m["set_id"]))
    return found[:TOP_MISSED]


def _practice(db: Session, course_id: UUID, students: frozenset[str], period: ReportingPeriod, topics: dict[UUID, str]) -> dict:
    rows = db.execute(
        select(PublishedPracticeSet.id, PublishedPracticeSet.title, PublishedPracticeSet.topic_id)
        .where(PublishedPracticeSet.course_id == course_id)
        .order_by(func.lower(PublishedPracticeSet.title), PublishedPracticeSet.id)
    ).all()
    set_ids = [str(row.id) for row in rows]
    questions: dict[str, list[tuple[str, int, str]]] = defaultdict(list)
    if set_ids:
        for q in db.execute(
            select(PublishedPracticeQuestion.id, PublishedPracticeQuestion.set_id, PublishedPracticeQuestion.position, PublishedPracticeQuestion.question)
            .where(PublishedPracticeQuestion.set_id.in_([row.id for row in rows]))
            .order_by(PublishedPracticeQuestion.position)
        ):
            questions[str(q.set_id)].append((str(q.id), q.position, q.question))
    by_set: dict[str, list[PeriodAttempts]] = defaultdict(list)
    for entry in submitted_in_period(set_ids, students, period.start, period.end):
        by_set[entry.set_id].append(entry)
    sets = []
    latest: dict[str, list[Attempt]] = {}
    for row in rows:
        set_id = str(row.id)
        entries = by_set[set_id]
        latest[set_id] = [e.latest for e in entries]
        correct = sum(a.score_correct for a in latest[set_id])
        total = sum(a.score_total for a in latest[set_id])
        sets.append({
            "set_id": set_id, "title": row.title, "topic": topics.get(row.topic_id, GENERAL_TOPIC),
            "students_attempted": len(entries), "submitted_attempts": sum(e.submitted_count for e in entries),
            "average_score_percent": _rate(correct, total),
        })
    return {"sets": sets, "missed_questions": _missed_questions(sets, questions, latest)}


def _course_report(db: Session, course_id: UUID, title: str, students: frozenset[str], period: ReportingPeriod) -> dict:
    topics = dict(db.execute(select(Topic.id, Topic.name).where(Topic.course_id == course_id)).all())
    stats = lesson_completion_stats(db, course_id, students, period.start, period.end)
    count = len(students)
    return {
        "course_id": str(course_id), "title": title, "student_count": count, "lesson_count": len(stats),
        "completion_rate_percent": _rate(sum(s.completed_students for s in stats), count * len(stats)),
        "lessons": [
            {
                "lesson_id": str(s.lesson_id), "title": s.title, "topic": topics.get(s.topic_id, GENERAL_TOPIC),
                "completed_students": s.completed_students, "rate_percent": _rate(s.completed_students, count),
            }
            for s in stats
        ],
        "practice": _practice(db, course_id, students, period, topics),
    }


def build_overview(db: Session, teacher_id: str, period: ReportingPeriod, now: datetime) -> dict:
    courses = member_courses(db, teacher_id)
    rosters = course_student_ids(db, [course_id for course_id, _ in courses])
    return {
        "period": period_json(period),
        "as_of": utc_timestamp(now),
        "courses": [_course_report(db, course_id, title, rosters[course_id], period) for course_id, title in courses],
    }
