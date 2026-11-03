"""Private, append-only MCQ drafts with current teacher/course access."""
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select

from errors import ApiError
from llm_client import LlmClient, get_llm_client
from teacher_materials.demo_identity import require_managed_course
from teacher_materials.models import CourseMembership, Material, McqDraftBatch, McqDraftQuestion, User
from teacher_materials.routes import _material_content
from teacher_access import owned_material, parse_uuid, teacher_session
from timestamps import utc_timestamp
from teacher_notes.generation import extract_source
from teacher_mcqs.generation import generate_mcqs

router = APIRouter(prefix="/api/teacher", tags=["teacher MCQ drafts"])


def _metadata(row):
    return dict(id=str(row.id), course_id=str(row.course_id), source_material_id=str(row.source_material_id),
                source_title=row.source_title, created_by=row.created_by, created_at=utc_timestamp(row.created_at), question_count=3)


def _detail(session, row):
    result = _metadata(row)
    questions = session.scalars(select(McqDraftQuestion).where(McqDraftQuestion.batch_id == row.id).order_by(McqDraftQuestion.position)).all()
    result["questions"] = [dict(id=str(q.id), position=q.position, question=q.question, choices=q.choices,
                                correct_choice_index=q.correct_choice_index, explanation=q.explanation) for q in questions]
    return result


@router.post("/materials/{material_id}/mcq-drafts", status_code=201)
def create_mcq_draft(request: Request, material_id: str, llm: LlmClient = Depends(get_llm_client)):
    with teacher_session(request) as (session, teacher):
        material = owned_material(session, teacher, material_id)
        teacher_id, source_id, course_id, title = teacher.id, material.id, material.course_id, material.title
        source_content, media_type = _material_content(session, material.id), material.media_type
    text = extract_source(source_content, media_type)
    questions = generate_mcqs(llm, text, teacher_id)
    with teacher_session(request) as (session, teacher):
        user = session.scalar(select(User).where(User.id == teacher_id).with_for_update(read=True).execution_options(populate_existing=True))
        if user is None or user.role != "teacher" or teacher.id != teacher_id:
            raise ApiError(403, "forbidden", "Teacher access is required.")
        membership = session.scalar(select(CourseMembership).where(CourseMembership.course_id == course_id, CourseMembership.user_id == teacher_id).with_for_update(read=True))
        source = session.scalar(select(Material).where(Material.id == source_id, Material.course_id == course_id).with_for_update(read=True))
        if membership is None or source is None:
            raise ApiError(404, "not_found", "Material not found.")
        row = McqDraftBatch(id=uuid4(), course_id=course_id, source_material_id=source_id, source_title=title,
                            created_by=teacher_id, created_at=datetime.now(timezone.utc))
        session.add(row)
        session.flush()
        session.add_all([McqDraftQuestion(id=uuid4(), batch_id=row.id, position=i, **q) for i, q in enumerate(questions, 1)])
        session.flush()
        payload = _detail(session, row)
        session.commit()
        return payload


@router.get("/courses/{course_id}/mcq-drafts")
def list_mcq_drafts(request: Request, course_id: str):
    with teacher_session(request) as (session, teacher):
        course = require_managed_course(session, teacher, parse_uuid(course_id))
        rows = session.scalars(select(McqDraftBatch).where(McqDraftBatch.course_id == course.id).order_by(McqDraftBatch.created_at.desc(), McqDraftBatch.id.desc())).all()
        return [_metadata(row) for row in rows]


@router.get("/mcq-drafts/{batch_id}")
def get_mcq_draft(request: Request, batch_id: str):
    with teacher_session(request) as (session, teacher):
        row = session.scalar(select(McqDraftBatch).join(CourseMembership, CourseMembership.course_id == McqDraftBatch.course_id).where(McqDraftBatch.id == parse_uuid(batch_id), CourseMembership.user_id == teacher.id))
        if row is None:
            raise ApiError(404, "not_found", "MCQ batch not found.")
        return _detail(session, row)
