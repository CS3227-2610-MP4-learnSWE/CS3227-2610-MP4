"""Development-only feedback seed: one open form with all six question types and a submitted response per seeded student.

Run after migrations and the auth seed:  uv run --env-file .env python -m feedback_dev_seed
Refuses unless APP_ENV=development. Rows are written the way the feedback routes write them (same validation, same
snapshot), so they look like recorded data. Idempotent: a form with the fixed title below marks it as applied.
It makes no AI call, no analysis and no message. Never run it where real feedback is collected.
"""
import os
import sys
from collections.abc import Mapping
from uuid import UUID, uuid4

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

import feedback_store as store
import feedback_validation as valid
from feedback_models import FeedbackForm, FeedbackRecipient, FeedbackResponse
from teacher_materials.models import User

TITLE = "Dev seed: course feedback"  # the marker
ADMIN = "demo-admin"


def _id(n: int) -> str:
    return str(UUID(int=0x5EED0000 + n))


def _questions() -> list[dict]:
    options = lambda base: [{"id": _id(base + i), "label": label} for i, label in enumerate(("Yes", "Somewhat", "No"))]
    scale = {"min": 1, "max": 5, "min_label": "Poor", "max_label": "Great"}
    return [
        {"id": _id(1), "type": "short_answer", "prompt": "What is one thing that works well?", "required": True, "options": [], "scale": None},
        {"id": _id(2), "type": "paragraph", "prompt": "What should we improve, and why?", "required": False, "options": [], "scale": None},
        {"id": _id(3), "type": "multiple_choice", "prompt": "Is the pace of the lessons right for you?", "required": True, "options": options(10), "scale": None},
        {"id": _id(4), "type": "dropdown", "prompt": "Which area do you use most?", "required": False,
         "options": [{"id": _id(20 + i), "label": label} for i, label in enumerate(("Lessons", "Practice", "Study companion"))], "scale": None},
        {"id": _id(5), "type": "checkbox", "prompt": "Which of these helped you?", "required": False,
         "options": [{"id": _id(30 + i), "label": label} for i, label in enumerate(("Hints", "Worked examples", "Progress charts"))], "scale": None},
        {"id": _id(6), "type": "linear_scale", "prompt": "How would you rate your overall experience?", "required": True, "options": [], "scale": scale},
    ]


# One answer set per seeded student, cycled; values are option ids or text of the questions above.
_ANSWERS = (
    ("The hints make me think instead of copying.", "Practice sets need a clearer explanation after submitting.", 10, 21, [30, 31], 4),
    ("Short lessons are easy to follow.", "", 11, 20, [32], 5),
    ("I like seeing my own progress.", "More examples would help with harder topics.", 12, 22, [30], 3),
)


def _answers(questions: list[dict], n: int) -> list[dict]:
    short, paragraph, pace, area, helped, rating = _ANSWERS[n % len(_ANSWERS)]
    values = (short, paragraph or None, _id(pace), _id(area), [_id(h) for h in helped], rating)
    return [{"question_id": q["id"], "value": v} for q, v in zip(questions, values)]


def seed(db: Session) -> str:
    if db.scalar(select(FeedbackForm.id).where(FeedbackForm.title == TITLE)) is not None:
        return "feedback dev seed: already applied"
    admin = db.get(User, ADMIN)
    students = db.scalars(select(User).where(User.role == "student", User.access_status == "enabled", User.archived_at.is_(None)).order_by(User.id)).all()
    if admin is None or not students:
        raise SystemExit("feedback dev seed: run the auth seed first (needs demo-admin and a student account)")
    data = valid.definition({"title": TITLE, "description": "Sample form created by the development seed.", "association": None, "questions": _questions()})
    row = FeedbackForm(**data, state="draft", version=1, created_by=admin.id, created_at=store.now(), updated_at=store.now())
    db.add(row)
    db.flush()
    for user in students:
        db.add(FeedbackRecipient(form_id=row.id, user_id=user.id, role_snapshot="student", display_name_snapshot=user.display_name, inbox_id=uuid4()))
    row.state, row.audience_role, row.published_at = "open", "student", store.now()
    row.updated_at, row.version = row.published_at, row.version + 1
    for n, user in enumerate(students):
        db.add(FeedbackResponse(form_id=row.id, user_id=user.id, display_name_snapshot=user.display_name, submitted_at=store.now(),
                                answers=valid.answers(_answers(row.questions, n), row.questions),
                                form_snapshot={"title": row.title, "description": row.description, "association": row.association, "questions": row.questions}))
    db.flush()
    count = db.scalar(select(func.count()).select_from(FeedbackResponse).where(FeedbackResponse.form_id == row.id))
    db.commit()
    return f"feedback dev seed: 1 open form, {count} response(s)"


def main(env: Mapping[str, str] = os.environ) -> int:
    if env.get("APP_ENV") != "development":
        print("The feedback seed is for development databases only (set APP_ENV=development).")
        return 1
    with Session(create_engine(env["DATABASE_URL"])) as db:
        print(seed(db))
    return 0


if __name__ == "__main__":
    sys.exit(main())
