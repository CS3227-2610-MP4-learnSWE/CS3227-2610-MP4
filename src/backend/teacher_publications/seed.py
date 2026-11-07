"""Development-only practice set seed. Run after migrations and teacher_materials.seed."""
import os
from collections.abc import Mapping
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from teacher_materials.models import Material, MaterialFile, McqDraftBatch, McqDraftQuestion
from teacher_publications.models import PublishedPracticeQuestion, PublishedPracticeSet

SEED_SET_ID = UUID("77777777-7777-4777-8777-777777777774")
_COURSE = UUID("11111111-1111-4111-8111-111111111111")
_TOPIC = UUID("66666666-6666-4666-8666-666666666661")
_TEACHER = "demo-teacher"
_MATERIAL = UUID("77777777-7777-4777-8777-777777777771")
_BATCH = UUID("77777777-7777-4777-8777-777777777772")
_SOURCE_TITLE = "Software engineering basics source"
_CONTENT = b"Software engineering basics: focused functions, automated tests and simple Python."
_QUESTIONS = (
    (
        "What should a well-designed function have?",
        ["A single, focused responsibility", "As many responsibilities as possible", "No descriptive name", "Hidden side effects only"],
        0,
        "One focused responsibility makes a function easier to understand, test and change.",
    ),
    (
        "Why do we keep automated tests alongside our code?",
        ["To make the repository larger", "To catch regressions when code changes", "To avoid ever reviewing code", "To slow down every release"],
        1,
        "Tests protect expected behaviour and can catch regressions introduced by later changes.",
    ),
    (
        "What does len([1, 2, 3]) return in Python?",
        ["2", "4", "3", "6"],
        2,
        "len returns the number of items. The list contains three items.",
    ),
)


def _uuid(n: int) -> UUID:
    return UUID(f"77777777-7777-4777-8777-7777777777{n}")


def _add_missing(session: Session, model, key, row) -> None:
    if session.get(model, key) is None:
        session.add(row)


def seed_practice_set(session: Session) -> None:
    """Create the seed rows that are missing; never update an existing one. Commits once."""
    _add_missing(session, Material, _MATERIAL, Material(
        id=_MATERIAL, course_id=_COURSE, topic_id=_TOPIC, uploaded_by=_TEACHER, title=_SOURCE_TITLE,
        original_filename="se-basics.txt", media_type="text/plain", size_bytes=len(_CONTENT)))
    session.flush()
    _add_missing(session, MaterialFile, _MATERIAL, MaterialFile(material_id=_MATERIAL, content=_CONTENT))
    _add_missing(session, McqDraftBatch, _BATCH, McqDraftBatch(
        id=_BATCH, course_id=_COURSE, source_material_id=_MATERIAL, created_by=_TEACHER,
        source_title=_SOURCE_TITLE, version=1, updated_by=_TEACHER))
    session.flush()
    for i, (text, choices, correct, explanation) in enumerate(_QUESTIONS, start=1):
        draft_id = _uuid(30 + i)
        _add_missing(session, McqDraftQuestion, draft_id, McqDraftQuestion(
            id=draft_id, batch_id=_BATCH, position=i, question=text, choices=choices,
            correct_choice_index=correct, explanation=explanation))
    session.flush()
    _add_missing(session, PublishedPracticeSet, SEED_SET_ID, PublishedPracticeSet(
        id=SEED_SET_ID, course_id=_COURSE, topic_id=_TOPIC, title="Software engineering practice",
        source_draft_id=_BATCH, source_version=1, published_by=_TEACHER))
    session.flush()
    for i, (text, choices, correct, explanation) in enumerate(_QUESTIONS, start=1):
        question_id = _uuid(50 + i)
        _add_missing(session, PublishedPracticeQuestion, question_id, PublishedPracticeQuestion(
            id=question_id, set_id=SEED_SET_ID, source_question_id=_uuid(30 + i), position=i, question=text,
            choices=choices, correct_choice_index=correct, explanation=explanation))
    session.commit()


def main(env: Mapping[str, str] = os.environ) -> int:
    if env.get("APP_ENV") != "development":
        print("The practice seed is for development databases only (set APP_ENV=development).")
        return 1
    with Session(create_engine(env["DATABASE_URL"])) as session:
        seed_practice_set(session)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
