"""Teacher materials HTTP API with access checks before request-body validation."""
from uuid import UUID, uuid4
from urllib.parse import quote

from fastapi import APIRouter, Request
from starlette.datastructures import UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from errors import ApiError
from teacher_access import owned_material, parse_uuid, teacher_session
from timestamps import utc_timestamp
from text_validation import is_postgres_text
from teacher_materials.demo_identity import require_managed_course
from teacher_materials.models import Course, CourseMembership, Material, MaterialFile, Topic
from teacher_materials.multipart import material_form
from teacher_materials.storage import MAX_TOTAL_BYTES, validate_upload

router = APIRouter(prefix="/api/teacher", tags=["teacher materials"])


def _course(row: Course) -> dict:
    return {"id": str(row.id), "title": row.title, "created_at": utc_timestamp(row.created_at)}


def _topic(row: Topic) -> dict:
    return {"id": str(row.id), "course_id": str(row.course_id), "name": row.name, "created_at": utc_timestamp(row.created_at)}


def _material(row: Material) -> dict:
    return {"id": str(row.id), "course_id": str(row.course_id), "topic_id": str(row.topic_id) if row.topic_id else None, "uploaded_by": row.uploaded_by, "title": row.title, "original_filename": row.original_filename, "media_type": row.media_type, "size_bytes": row.size_bytes, "created_at": utc_timestamp(row.created_at), "updated_at": utc_timestamp(row.updated_at)}


def _same_course_topic(session: Session, course_id: UUID, value: str) -> UUID:
    topic_id = parse_uuid(value)
    if session.scalar(select(Topic.id).where(Topic.id == topic_id, Topic.course_id == course_id)) is None:
        raise ApiError(404, "not_found", "Topic not found.")
    return topic_id


@router.get("/courses")
def list_courses(request: Request):
    with teacher_session(request) as (session, teacher):
        rows = session.scalars(select(Course).join(CourseMembership, CourseMembership.course_id == Course.id).where(CourseMembership.user_id == teacher.id).order_by(Course.created_at, Course.id)).all()
        return [_course(row) for row in rows]


@router.get("/courses/{course_id}/topics")
def list_topics(request: Request, course_id: str):
    with teacher_session(request) as (session, teacher):
        course = require_managed_course(session, teacher, parse_uuid(course_id))
        rows = session.scalars(select(Topic).where(Topic.course_id == course.id).order_by(Topic.created_at, Topic.id)).all()
        return [_topic(row) for row in rows]


@router.get("/courses/{course_id}/materials")
def list_materials(request: Request, course_id: str):
    with teacher_session(request) as (session, teacher):
        course = require_managed_course(session, teacher, parse_uuid(course_id))
        query = select(Material).where(Material.course_id == course.id)
        if "topic_id" in request.query_params:
            topic_id = _same_course_topic(session, course.id, request.query_params["topic_id"])
            query = query.where(Material.topic_id == topic_id)
        rows = session.scalars(query.order_by(Material.created_at.desc(), Material.id)).all()
        return [_material(row) for row in rows]


@router.post("/courses/{course_id}/materials", status_code=201)
async def upload_material(request: Request, course_id: str):
    with teacher_session(request) as (session, teacher):
        course = require_managed_course(session, teacher, parse_uuid(course_id))
        async with material_form(request) as form:
            allowed = {"file", "title", "topic_id"}
            if (set(form.keys()) - allowed
                    or any(len(form.getlist(key)) != 1 for key in form)
                    or not isinstance(form.get("file"), UploadFile)
                    or not isinstance(form.get("title"), str)
                    or ("topic_id" in form and not isinstance(form["topic_id"], str))):
                raise ApiError(422, "validation_error", "A title, optional topic and exactly one file are required.")
            title = form["title"].strip()
            if not 1 <= len(title) <= 200 or not is_postgres_text(title):
                raise ApiError(422, "validation_error", "Title must contain 1–200 characters.")
            topic_id = _same_course_topic(session, course.id, form["topic_id"]) if form.get("topic_id") else None
            stored = validate_upload(form["file"])
            # A transaction-scoped lock makes the fresh byte sum safe for concurrent uploads.
            session.execute(text("SELECT pg_advisory_xact_lock(32272610)"))
            used = session.scalar(select(func.coalesce(func.sum(func.octet_length(MaterialFile.content)), 0)))
            if used + stored.size_bytes > MAX_TOTAL_BYTES:
                raise ApiError(413, "storage_quota_exceeded", "Upload would exceed the 100 MiB total storage limit.")
            row = Material(id=uuid4(), course_id=course.id, topic_id=topic_id, uploaded_by=teacher.id, title=title, original_filename=stored.original_filename, media_type=stored.media_type, size_bytes=stored.size_bytes)
            session.add(row)
            session.flush()
            session.add(MaterialFile(material_id=row.id, content=stored.content))
            session.flush()
            session.refresh(row)
            payload = _material(row)
            session.commit()
            return payload


class TopicPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topic_id: UUID | None


@router.patch("/materials/{material_id}")
async def assign_topic(request: Request, material_id: str):
    with teacher_session(request) as (session, teacher):
        row = owned_material(session, teacher, material_id)
        try:
            body = TopicPatch.model_validate(await request.json())
        except (ValueError, ValidationError) as exc:
            raise ApiError(422, "validation_error", "Provide only a valid topic_id UUID or null.") from exc
        topic_id = _same_course_topic(session, row.course_id, str(body.topic_id)) if body.topic_id else None
        # Lock row so the last committed assignment wins and unrelated columns stay untouched.
        row = session.scalar(select(Material).where(Material.id == row.id).with_for_update().execution_options(populate_existing=True))
        row.topic_id = topic_id
        row.updated_at = func.now()
        session.flush()
        session.refresh(row)
        payload = _material(row)
        session.commit()
        return payload


def _material_content(session: Session, material_id: UUID) -> bytes:
    content = session.scalar(select(MaterialFile.content).where(MaterialFile.material_id == material_id))
    if content is None:
        raise ApiError(503, "service_unavailable", "Stored material content is unavailable.")
    return content


@router.get("/materials/{material_id}/file")
def download_material(request: Request, material_id: str):
    with teacher_session(request) as (session, teacher):
        row = owned_material(session, teacher, material_id)
        content = _material_content(session, row.id)
        filename = quote(row.original_filename)
        disposition = f"attachment; filename*=utf-8''{filename}" if filename != row.original_filename else f'attachment; filename="{filename}"'
        return Response(content, media_type=row.media_type, headers={"Content-Disposition": disposition})
