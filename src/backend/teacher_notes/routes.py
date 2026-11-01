"""Authorised, append-only study-note drafts; no transaction during model calls."""
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select

from errors import ApiError
from llm_client import LlmClient, get_llm_client
from teacher_materials.demo_identity import require_managed_course
from teacher_materials.models import CourseMembership, Material, StudyNoteDraft, User
from teacher_materials.routes import _owned_material, _teacher_session, _timestamp, _uuid
from teacher_materials.storage import resolve_file, storage_root
from teacher_notes.generation import extract_source, generate_notes

router = APIRouter(prefix="/api/teacher", tags=["teacher note drafts"])


def _draft(row: StudyNoteDraft, *, content: bool = False) -> dict:
    result = {"id": str(row.id), "course_id": str(row.course_id), "source_material_id": str(row.source_material_id), "created_by": row.created_by, "title": row.title, "created_at": _timestamp(row.created_at)}
    if content:
        result["content"] = row.content
    return result


@router.post("/materials/{material_id}/note-drafts", status_code=201)
def create_note_draft(request: Request, material_id: str, llm: LlmClient = Depends(get_llm_client)):
    with _teacher_session(request) as (session, teacher):
        material = _owned_material(session, teacher, material_id)
        teacher_id, source_id, course_id, title = teacher.id, material.id, material.course_id, material.title
        path = resolve_file(storage_root(), material.storage_key)
        media_type = material.media_type
    # Copy scalars and release the session before extraction and external work.
    text = extract_source(path, media_type)
    content = generate_notes(llm, text, teacher_id)
    with _teacher_session(request) as (session, teacher):
        # Locks linearise access checks with concurrent role/membership changes.
        user = session.scalar(select(User).where(User.id == teacher_id).with_for_update(read=True).execution_options(populate_existing=True))
        if user is None or user.role != "teacher" or teacher.id != teacher_id:
            raise ApiError(403, "forbidden", "Teacher access is required.")
        membership = session.scalar(select(CourseMembership).where(CourseMembership.course_id == course_id, CourseMembership.user_id == teacher_id).with_for_update(read=True))
        source = session.scalar(select(Material).where(Material.id == source_id, Material.course_id == course_id).with_for_update(read=True))
        if membership is None or source is None:
            raise ApiError(404, "not_found", "Material not found.")
        row = StudyNoteDraft(id=uuid4(), course_id=course_id, source_material_id=source_id, created_by=teacher_id, title=title, content=content)
        session.add(row)
        session.flush()
        session.refresh(row)
        payload = _draft(row, content=True)
        session.commit()
        return payload


@router.get("/courses/{course_id}/note-drafts")
def list_note_drafts(request: Request, course_id: str):
    with _teacher_session(request) as (session, teacher):
        course = require_managed_course(session, teacher, _uuid(course_id))
        rows = session.scalars(select(StudyNoteDraft).where(StudyNoteDraft.course_id == course.id).order_by(StudyNoteDraft.created_at.desc(), StudyNoteDraft.id.desc())).all()
        return [_draft(row) for row in rows]


@router.get("/note-drafts/{draft_id}")
def get_note_draft(request: Request, draft_id: str):
    with _teacher_session(request) as (session, teacher):
        row = session.scalar(select(StudyNoteDraft).join(CourseMembership, CourseMembership.course_id == StudyNoteDraft.course_id).where(StudyNoteDraft.id == _uuid(draft_id), CourseMembership.user_id == teacher.id))
        if row is None:
            raise ApiError(404, "not_found", "Draft not found.")
        return _draft(row, content=True)
