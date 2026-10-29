"""Validation and scoring for practice attempts."""
from practice_data import PracticeSet


def validate_answers(practice_set: PracticeSet, answers: dict[str, str]) -> tuple[str, str] | None:
    """Return (error_code, message) for the first invalid entry, else None."""
    questions = {q.id: q for q in practice_set.questions}
    for question_id, choice_id in answers.items():
        question = questions.get(question_id)
        if question is None:
            return "unknown_question", "Unknown question in answers."
        if choice_id not in {cid for cid, _ in question.choices}:
            return "invalid_choice", "Choice does not belong to the question."
    return None


def missing_questions(practice_set: PracticeSet, answers: dict[str, str]) -> list[str]:
    return [q.id for q in practice_set.questions if q.id not in answers]


def score(practice_set: PracticeSet, answers: dict[str, str]) -> dict[str, int]:
    correct = sum(1 for q in practice_set.questions if answers.get(q.id) == q.correct)
    return {"correct": correct, "total": len(practice_set.questions)}
