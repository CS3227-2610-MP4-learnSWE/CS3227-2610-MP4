"""Validation and scoring. The only place the answer key is read."""
from errors import ApiError
from practice_data import KEY_VERSION, PracticeSet
from practice_schemas import ResultQuestion, ResultsOut, Score


def validate_answers(practice_set: PracticeSet, answers: dict[str, str]) -> None:
    questions = {q.id: q for q in practice_set.questions}
    for qid, choice in answers.items():
        question = questions.get(qid)
        if question is None:
            raise ApiError(422, "unknown_question", "Answer refers to a question not in this set.")
        if choice not in {cid for cid, _ in question.choices}:
            raise ApiError(422, "invalid_choice", "Choice does not belong to the question.")


def missing_questions(practice_set: PracticeSet, answers: dict[str, str]) -> list[str]:
    return [q.id for q in practice_set.questions if q.id not in answers]


def score(practice_set: PracticeSet, answers: dict[str, str]) -> Score:
    correct = sum(1 for q in practice_set.questions if answers.get(q.id) == q.correct)
    return Score(correct=correct, total=len(practice_set.questions))


def build_results(
    attempt_id: str, set_id: str, practice_set: PracticeSet, answers: dict[str, str]
) -> ResultsOut:
    return ResultsOut(
        attempt_id=attempt_id,
        set_id=set_id,
        key_version=KEY_VERSION,
        score=score(practice_set, answers),
        answers=answers,
        questions=[
            ResultQuestion(
                id=q.id,
                selected=answers[q.id],
                correct_choice=q.correct,
                correct=answers[q.id] == q.correct,
                explanation=q.explanation,
            )
            for q in practice_set.questions
        ],
    )
