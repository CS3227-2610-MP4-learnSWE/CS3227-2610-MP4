"""Private note generation and versioned edits with current course access."""
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, ValidationError

from errors import ApiError
from text_validation import is_postgres_text, normalise_newlines_and_trim
from llm_client import LlmClient, get_llm_client
from teacher_access import owned_material, parse_uuid, teacher_session
from teacher_materials.demo_identity import require_managed_course
from teacher_materials.models import CourseMembership, Material, StudyNoteDraft, User
from teacher_materials.storage import resolve_file, storage_root
from timestamps import utc_timestamp
from teacher_notes.generation import extract_source, generate_notes

router = APIRouter(prefix="/api/teacher", tags=["teacher note drafts"])


def _draft(row: StudyNoteDraft, *, content: bool = False) -> dict:
    result = {"id": str(row.id), "course_id": str(row.course_id), "source_material_id": str(row.source_material_id), "created_by": row.created_by, "title": row.title, "created_at": utc_timestamp(row.created_at), "source_title": row.source_title, "version": row.version, "updated_at": utc_timestamp(row.updated_at), "updated_by": row.updated_by}
    if content:
        result["content"] = row.content
    return result


@router.post("/materials/{material_id}/note-drafts", status_code=201)
def create_note_draft(request: Request, material_id: str, llm: LlmClient = Depends(get_llm_client)):
    with teacher_session(request) as (session, teacher):
        material = owned_material(session, teacher, material_id)
        teacher_id, source_id, course_id, title = teacher.id, material.id, material.course_id, material.title
        path = resolve_file(storage_root(), material.storage_key)
        media_type = material.media_type
    # Copy scalars and release the session before extraction and external work.
    text = extract_source(path, media_type)
    content = generate_notes(llm, text, teacher_id)
    with teacher_session(request) as (session, teacher):
        # Locks linearise access checks with concurrent role/membership changes.
        user = session.scalar(select(User).where(User.id == teacher_id).with_for_update(read=True).execution_options(populate_existing=True))
        if user is None or user.role != "teacher" or teacher.id != teacher_id:
            raise ApiError(403, "forbidden", "Teacher access is required.")
        membership = session.scalar(select(CourseMembership).where(CourseMembership.course_id == course_id, CourseMembership.user_id == teacher_id).with_for_update(read=True))
        source = session.scalar(select(Material).where(Material.id == source_id, Material.course_id == course_id).with_for_update(read=True))
        if membership is None or source is None:
            raise ApiError(404, "not_found", "Material not found.")
        created = datetime.now(timezone.utc)
        row = StudyNoteDraft(id=uuid4(), course_id=course_id, source_material_id=source_id, created_by=teacher_id, title=title, source_title=title, content=content, version=1, updated_by=teacher_id, created_at=created, updated_at=created)
        session.add(row)
        session.flush()
        session.refresh(row)
        payload = _draft(row, content=True)
        session.commit()
        return payload


@router.get("/courses/{course_id}/note-drafts")
def list_note_drafts(request: Request, course_id: str):
    with teacher_session(request) as (session, teacher):
        course = require_managed_course(session, teacher, parse_uuid(course_id))
        rows = session.scalars(select(StudyNoteDraft).where(StudyNoteDraft.course_id == course.id).order_by(StudyNoteDraft.created_at.desc(), StudyNoteDraft.id.desc())).all()
        return [_draft(row) for row in rows]


@router.get("/note-drafts/{draft_id}")
def get_note_draft(request: Request, draft_id: str):
    with teacher_session(request) as (session, teacher):
        row = session.scalar(select(StudyNoteDraft).join(CourseMembership, CourseMembership.course_id == StudyNoteDraft.course_id).where(StudyNoteDraft.id == parse_uuid(draft_id), CourseMembership.user_id == teacher.id))
        if row is None:
            raise ApiError(404, "not_found", "Draft not found.")
        return _draft(row, content=True)


class DraftEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: StrictStr
    content: StrictStr
    version: StrictInt = Field(ge=1)


def _edit_error() -> ApiError:
    return ApiError(422, "validation_error", "Provide a valid title, note content and positive integer version.")


@router.patch("/note-drafts/{draft_id}")
async def edit_note_draft(request: Request, draft_id: str):
    try:
        with teacher_session(request) as (session, teacher):
            try:
                identifier = parse_uuid(draft_id)
            except ApiError:
                raise _edit_error() from None
            row = session.scalar(select(StudyNoteDraft).join(CourseMembership, CourseMembership.course_id == StudyNoteDraft.course_id).where(StudyNoteDraft.id == identifier, CourseMembership.user_id == teacher.id))
            if row is None:
                raise ApiError(404, "not_found", "Draft not found.")
            try:
                body = DraftEdit.model_validate(await request.json())
            except (ValueError, ValidationError):
                raise _edit_error() from None
            title = body.title.strip()
            content = normalise_newlines_and_trim(body.content)
            if not 1 <= len(title) <= 200 or not 1 <= len(content) <= 2000 or not is_postgres_text(title + content):
                raise _edit_error()
            # Shared locks hold role/membership stable until the versioned write commits.
            user = session.scalar(select(User).where(User.id == teacher.id).with_for_update(read=True).execution_options(populate_existing=True))
            if user is None or user.role != "teacher":
                raise ApiError(403, "forbidden", "Teacher access is required.")
            membership = session.scalar(select(CourseMembership).where(CourseMembership.course_id == row.course_id, CourseMembership.user_id == teacher.id).with_for_update(read=True))
            if membership is None:
                raise ApiError(404, "not_found", "Draft not found.")
            row = session.scalar(select(StudyNoteDraft).where(StudyNoteDraft.id == identifier).with_for_update().execution_options(populate_existing=True))
            if row is None:
                raise ApiError(404, "not_found", "Draft not found.")
            if row.version != body.version:
                raise ApiError(409, "draft_conflict", "This draft has changed. Load the latest saved version before saving.")
            row.title, row.content = title, content
            row.version += 1
            row.updated_by = user.id
            row.updated_at = datetime.now(timezone.utc)
            session.flush()
            session.refresh(row)
            payload = _draft(row, content=True)
            session.commit()
            return payload
    except ApiError as exc:
        if exc.status == 503:
            raise ApiError(503, "service_unavailable", "Teacher notes service is unavailable. Please try again.") from None
        raise
