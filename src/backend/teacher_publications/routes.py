"""Publish saved drafts and read immutable, course-authorised snapshots."""
import json
from contextlib import contextmanager
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from auth.dependencies import AuthUser, current_user
from errors import ApiError
from practice_schemas import public_set
from set_provider import SetProvider, get_set_provider
from study_lessons.models import PublishedLesson
from study_lessons.publish import publish_lesson
from teacher_access import parse_uuid, require_managed_course, teacher_session
from teacher_materials.models import CourseMembership, McqDraftBatch, McqDraftQuestion, StudyNoteDraft, Topic
from teacher_mcqs.generation import validate_questions
from teacher_publications.models import PublishedPracticeQuestion, PublishedPracticeSet
from text_validation import is_postgres_text
from timestamps import utc_timestamp

router = APIRouter(tags=["published content"])


def invalid() -> ApiError:
    return ApiError(422, "validation_error", "Provide a valid title, course topic and positive integer draft version.")


@contextmanager
def publication_errors():
    try:
        yield
    except SQLAlchemyError:
        raise ApiError(503, "service_unavailable", "Published content service is unavailable. Please try again.") from None
    except ApiError as error:
        if error.status == 503:
            raise ApiError(503, "service_unavailable", "Published content service is unavailable. Please try again.") from None
        raise


class PublishIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: StrictInt = Field(ge=1)
    title: StrictStr
    topic_id: StrictStr


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate field")
        result[key] = value
    return result


async def publication_input(request: Request) -> tuple[PublishIn, UUID]:
    try:
        data = json.loads(await request.body(), object_pairs_hook=unique_object)
        body = PublishIn.model_validate(data)
        body.title = body.title.strip()
        topic_id = UUID(body.topic_id)
        if not 1 <= len(body.title) <= 200 or not is_postgres_text(body.title):
            raise ValueError("Invalid title")
        return body, topic_id
    except (ValueError, TypeError, RecursionError, ValidationError):
        raise invalid() from None


def metadata(db: Session, row, kind: str, *, teacher: bool = True, topics=None) -> dict:
    topic_name = (topics or {}).get(row.topic_id)
    if topic_name is None:
        topic = db.get(Topic, row.topic_id) if row.topic_id else None
        topic_name = topic.name if topic else "General"
    result = dict(id=str(row.id), kind=kind, course_id=str(row.course_id), topic_id=str(row.topic_id) if row.topic_id else None,
                  topic_name=topic_name, title=row.title, published_at=utc_timestamp(row.published_at))
    if kind == "practice_set":
        result["question_count"] = 3
    if teacher:
        result.update(source_draft_id=str(row.source_draft_id) if row.source_draft_id else None,
                      source_version=row.source_version, published_by=row.published_by,
                      withdrawn=kind == "note" and row.withdrawn_at is not None)
    return result


def detail(db: Session, row, kind: str) -> dict:
    result = metadata(db, row, kind)
    if kind == "note":
        result["content"] = row.content
    else:
        result["questions"] = [dict(id=str(q.id), position=q.position, question=q.question, choices=q.choices,
                                    correct_choice_index=q.correct_choice_index, explanation=q.explanation)
                               for q in questions(db, row.id)]
    return result


def questions(db: Session, set_id: UUID):
    return db.scalars(select(PublishedPracticeQuestion).where(PublishedPracticeQuestion.set_id == set_id).order_by(PublishedPracticeQuestion.position)).all()


def owned(db: Session, teacher: AuthUser, model, identifier: str, *, name: str):
    row = db.scalar(select(model).join(CourseMembership, CourseMembership.course_id == model.course_id)
                    .where(model.id == parse_uuid(identifier), CourseMembership.user_id == teacher.id))
    if row is None:
        raise ApiError(404, "not_found", f"{name} not found.")
    require_managed_course(db, teacher, row.course_id)
    return row


def existing_publication(db, model, source_id, body, topic_id, kind):
    rows = db.scalars(select(model).where(model.source_draft_id == source_id)).all()
    if not rows:
        return None
    if len(rows) == 1 and rows[0].source_version == body.version and rows[0].title == body.title and rows[0].topic_id == topic_id:
        return detail(db, rows[0], kind)
    raise ApiError(409, "already_published", "This draft has already been published.")


async def publish(request: Request, identifier: str, kind: str):
    source_model = StudyNoteDraft if kind == "note" else McqDraftBatch
    published_model = PublishedLesson if kind == "note" else PublishedPracticeSet
    with publication_errors(), teacher_session(request) as (db, teacher):
        source = owned(db, teacher, source_model, identifier, name="Draft")
        body, topic_id = await publication_input(request)
        if db.scalar(select(Topic.id).where(Topic.id == topic_id, Topic.course_id == source.course_id)) is None:
            raise ApiError(404, "not_found", "Topic not found.")
        source = db.scalar(select(source_model).where(source_model.id == source.id).with_for_update().execution_options(populate_existing=True))
        if source is None:
            raise ApiError(404, "not_found", "Draft not found.")
        topic = db.scalar(select(Topic).where(Topic.id == topic_id, Topic.course_id == source.course_id).with_for_update(read=True))
        if topic is None:
            raise ApiError(404, "not_found", "Topic not found.")
        previous = existing_publication(db, published_model, source.id, body, topic_id, kind)
        if previous is not None:
            return JSONResponse(previous, status_code=200)
        if source.version != body.version:
            raise ApiError(409, "draft_conflict", "This draft has changed. Reload and review it before publishing.")
        if kind == "note":
            if not isinstance(source.content, str) or not source.content.strip() or len(source.content) > 2000 or not is_postgres_text(source.content):
                raise invalid()
            row = publish_lesson(db, source, teacher, title=body.title, topic_id=topic_id)
        else:
            saved = db.scalars(select(McqDraftQuestion).where(McqDraftQuestion.batch_id == source.id).order_by(McqDraftQuestion.position)).all()
            try:
                if [q.position for q in saved] != [1, 2, 3]:
                    raise ValueError("Incomplete batch")
                values = [dict(question=q.question, choices=q.choices, correct_choice_index=q.correct_choice_index, explanation=q.explanation) for q in saved]
                if validate_questions(values) != values:
                    raise ValueError("Noncanonical saved questions")
            except (ValueError, TypeError):
                raise invalid() from None
            try:
                with db.begin_nested():
                    row = PublishedPracticeSet(id=uuid4(), course_id=source.course_id, topic_id=topic_id, title=body.title,
                                               source_draft_id=source.id, source_version=source.version, published_by=teacher.id)
                    db.add(row)
                    db.flush()
                    db.add_all([PublishedPracticeQuestion(id=uuid4(), set_id=row.id, source_question_id=q.id, position=q.position,
                                                          **value) for q, value in zip(saved, values)])
                    db.flush()
                    db.refresh(row)
            except IntegrityError as error:
                constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", "")
                if getattr(error.orig, "sqlstate", None) != "23505" or constraint != "published_practice_set_source_draft_id_key":
                    raise
                previous = existing_publication(db, published_model, source.id, body, topic_id, kind)
                if previous is None:
                    raise
                return JSONResponse(previous, status_code=200)
        payload = detail(db, row, kind)
        db.commit()
        return JSONResponse(payload, status_code=201)


@router.post("/api/teacher/note-drafts/{draft_id}/publish")
async def publish_note(request: Request, draft_id: str):
    return await publish(request, draft_id, "note")


@router.post("/api/teacher/mcq-drafts/{batch_id}/publish")
async def publish_set(request: Request, batch_id: str):
    return await publish(request, batch_id, "practice_set")


@router.get("/api/teacher/courses/{course_id}/publications")
def list_publications(request: Request, course_id: str):
    with publication_errors(), teacher_session(request) as (db, teacher):
        course = require_managed_course(db, teacher, parse_uuid(course_id))
        entries = [("note", row) for row in db.scalars(select(PublishedLesson).where(PublishedLesson.course_id == course.id))]
        entries += [("practice_set", row) for row in db.scalars(select(PublishedPracticeSet).where(PublishedPracticeSet.course_id == course.id))]
        entries.sort(key=lambda item: item[0])
        entries.sort(key=lambda item: (item[1].published_at, item[1].id.int), reverse=True)
        topics = dict(db.execute(select(Topic.id, Topic.name).where(Topic.course_id == course.id)).all())
        return [metadata(db, row, kind, topics=topics) for kind, row in entries]


@router.get("/api/teacher/published-notes/{publication_id}")
def read_note(request: Request, publication_id: str):
    with publication_errors(), teacher_session(request) as (db, teacher):
        return detail(db, owned(db, teacher, PublishedLesson, publication_id, name="Publication"), "note")


@router.get("/api/teacher/published-practice-sets/{publication_id}")
def read_set(request: Request, publication_id: str):
    with publication_errors(), teacher_session(request) as (db, teacher):
        return detail(db, owned(db, teacher, PublishedPracticeSet, publication_id, name="Publication"), "practice_set")


@router.get("/api/study/courses/{course_id}/practice-sets")
def student_sets(course_id: str, user: AuthUser = Depends(current_user(role="student")), provider: SetProvider = Depends(get_set_provider)):
    with publication_errors():
        catalog = provider.catalog_for_student(user.id, course_id=parse_uuid(course_id))
        if not catalog:
            raise ApiError(404, "not_found", "Course not found.")
        course = catalog[0]
        return [dict(id=s.id, kind="practice_set", course_id=course.id, topic_id=s.topic_id, topic_name=s.topic_name, title=s.title,
                     published_at=utc_timestamp(s.published_at), question_count=s.question_count) for s in course.sets]


@router.get("/api/study/practice-sets/{set_id}")
def student_set(set_id: str, user: AuthUser = Depends(current_user(role="student")), provider: SetProvider = Depends(get_set_provider)):
    with publication_errors():
        practice_set = provider.get_for_student(str(parse_uuid(set_id)), user.id)
        if practice_set is None:
            raise ApiError(404, "not_found", "Publication not found.")
        return public_set(practice_set)
