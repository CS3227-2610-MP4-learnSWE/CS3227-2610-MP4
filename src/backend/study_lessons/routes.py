"""Student study endpoints: courses, lessons, and the completion state. Student role only."""
import re
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from auth.db import get_session
from auth.dependencies import AuthUser, current_user, require_course_member
from errors import ApiError
from study_lessons import schemas
from study_lessons.access import get_visible_lesson, visible_lessons
from study_lessons.models import LessonCompletion, PublishedLesson
from study_lessons.progress import CourseCounts, completion_counts, member_courses, set_completion
from teacher_materials.models import Course, Topic
from timestamps import utc_timestamp

MAX_LESSONS = 500
EXCERPT_LENGTH = 160
GENERAL = "General"


router = APIRouter(prefix="/api/study")  # Cache-Control: no-store is set by the add_no_store middleware
student = Depends(current_user(role="student"))


def _excerpt(content: str) -> str:
    return re.sub(r"\s+", " ", content).strip()[:EXCERPT_LENGTH]


def _parse_completion(raw: bytes) -> schemas.CompletionRequest:
    """Strict body parse; the 422 names the offending fields, never their values."""
    try:
        return schemas.CompletionRequest.model_validate_json(raw)
    except ValidationError as exc:
        fields = sorted({str(e["loc"][0]) for e in exc.errors() if e["loc"]})
        raise ApiError(422, "validation_error", "Provide a valid request.", fields=fields) from None


@router.get("/courses")
def list_courses(user: AuthUser = student, db: Session = Depends(get_session)) -> schemas.CourseListOut:
    counts = completion_counts(db, user.id)
    items = []
    for cid, title in member_courses(db, user.id):
        c = counts.get(cid, CourseCounts(0, 0))
        items.append(schemas.CourseSummary(id=str(cid), title=title, lesson_count=c.lesson_count, completed_count=c.completed_count))
    totals = schemas.CourseCountsOut(
        lesson_count=sum(c.lesson_count for c in items), completed_count=sum(c.completed_count for c in items)
    )
    return schemas.CourseListOut(courses=items, totals=totals)


@router.get("/courses/{course_id}/lessons")
def list_lessons(course_id: UUID, user: AuthUser = student, db: Session = Depends(get_session)) -> schemas.LessonListOut:
    course = require_course_member(db, user, course_id)
    rows = db.execute(
        visible_lessons(user)
        .add_columns(Topic.name)
        .outerjoin(Topic, Topic.id == PublishedLesson.topic_id)
        .where(PublishedLesson.course_id == course.id)
        .order_by(PublishedLesson.published_at, PublishedLesson.id)
        .limit(MAX_LESSONS)
    ).all()
    done = set(
        db.scalars(
            select(LessonCompletion.lesson_id).where(
                LessonCompletion.user_id == user.id, LessonCompletion.course_id == course.id, LessonCompletion.completed.is_(True)
            )
        )
    )
    groups: dict[UUID | None, schemas.TopicGroup] = {}
    for lesson, topic_name in rows:
        topic_id = lesson.topic_id
        group = groups.setdefault(topic_id, schemas.TopicGroup(id=None if topic_id is None else str(topic_id), name=topic_name or GENERAL, lessons=[]))
        group.lessons.append(schemas.LessonSummary(id=str(lesson.id), title=lesson.title, excerpt=_excerpt(lesson.content), completed=lesson.id in done))
    ordered = sorted(groups.items(), key=lambda item: (item[0] is None, item[1].name.lower(), str(item[0])))
    return schemas.LessonListOut(
        course=schemas.CourseRef(id=str(course.id), title=course.title), topics=[group for _, group in ordered]
    )


@router.get("/lessons/{lesson_id}")
def read_lesson(lesson_id: UUID, user: AuthUser = student, db: Session = Depends(get_session)) -> schemas.LessonOut:
    lesson = get_visible_lesson(db, user, lesson_id)
    course = db.get(Course, lesson.course_id)
    topic = db.get(Topic, lesson.topic_id) if lesson.topic_id else None
    completion = db.get(LessonCompletion, (user.id, lesson.id))
    completed_at = completion.completed_at if completion and completion.completed else None
    return schemas.LessonOut(
        id=str(lesson.id),
        course=schemas.CourseRef(id=str(course.id), title=course.title),
        topic=schemas.TopicRef(id=str(topic.id) if topic else None, name=topic.name if topic else GENERAL),
        title=lesson.title,
        content=lesson.content,
        published_at=utc_timestamp(lesson.published_at),
        completed=completed_at is not None,
        completed_at=None if completed_at is None else utc_timestamp(completed_at),
    )


async def _raw_body(request: Request) -> bytes:
    return await request.body()


@router.put("/lessons/{lesson_id}/completion")
def put_completion(
    lesson_id: UUID, raw: bytes = Depends(_raw_body), user: AuthUser = student, db: Session = Depends(get_session)
) -> schemas.CompletionOut:
    get_visible_lesson(db, user, lesson_id)  # 404 before body validation
    body = _parse_completion(raw)
    row = set_completion(db, user, lesson_id, body.completed)
    counts = completion_counts(db, user.id, [row.course_id]).get(row.course_id, CourseCounts(0, 0))
    return schemas.CompletionOut(
        lesson_id=str(row.lesson_id),
        completed=row.completed,
        completed_at=None if row.completed_at is None else utc_timestamp(row.completed_at),
        course=schemas.CompletionCourse(id=str(row.course_id), lesson_count=counts.lesson_count, completed_count=counts.completed_count),
    )
