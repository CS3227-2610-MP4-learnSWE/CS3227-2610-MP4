"""Validation and scoring. The only place the answer key is read."""
from practice_data import KEY_VERSION, PracticeSet


class AnswerError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def validate_answers(practice_set: PracticeSet, answers: dict[str, str]) -> None:
    """Raise AnswerError if any answer is invalid. Never reveals the key."""
    questions = {q.id: q for q in practice_set.questions}
    for question_id, choice_id in answers.items():
        question = questions.get(question_id)
        if question is None:
            raise AnswerError("unknown_question", "Answer refers to a question not in this set.")
        if choice_id not in {c.id for c in question.choices}:
            raise AnswerError("invalid_choice", "Selected choice does not belong to the question.")


def missing_questions(practice_set: PracticeSet, answers: dict[str, str]) -> list[str]:
    return [q.id for q in practice_set.questions if q.id not in answers]


def score(practice_set: PracticeSet, answers: dict[str, str]) -> dict[str, int]:
    correct = sum(1 for q in practice_set.questions if answers.get(q.id) == q.correct_choice)
    return {"correct": correct, "total": len(practice_set.questions)}


def build_results(practice_set: PracticeSet, answers: dict[str, str]) -> dict:
    """Call only for a submitted attempt."""
    return {
        "key_version": KEY_VERSION,
        "score": score(practice_set, answers),
        "answers": dict(answers),
        "questions": [
            {
                "id": q.id,
                "selected": answers[q.id],
                "correct_choice": q.correct_choice,
                "correct": answers[q.id] == q.correct_choice,
                "explanation": q.explanation,
            }
            for q in practice_set.questions
        ],
    }
