"""Request and response schemas for the practice attempt API."""
from pydantic import BaseModel

from practice_data import PracticeSet


class ChoiceOut(BaseModel):
    id: str
    text: str


class QuestionOut(BaseModel):
    id: str
    text: str
    code: str | None
    choices: list[ChoiceOut]


class PracticeSetOut(BaseModel):
    id: str
    title: str
    questions: list[QuestionOut]


def public_set(practice_set: PracticeSet) -> PracticeSetOut:
    """The one answer-free view of a set: never the correct choice or the explanation."""
    return PracticeSetOut(
        id=practice_set.id,
        title=practice_set.title,
        questions=[
            QuestionOut(
                id=q.id, text=q.text, code=q.code, choices=[ChoiceOut(id=c, text=t) for c, t in q.choices]
            )
            for q in practice_set.questions
        ],
    )


class AttemptOut(BaseModel):
    attempt_id: str
    set_id: str
    status: str
    answers: dict[str, str]


class AnswersIn(BaseModel):
    answers: dict[str, str]


class AnswersSaved(BaseModel):
    attempt_id: str
    status: str
    answers: dict[str, str]


class Score(BaseModel):
    correct: int
    total: int


class SubmitOut(BaseModel):
    attempt_id: str
    status: str
    score: Score


class ResultQuestion(BaseModel):
    id: str
    selected: str
    correct_choice: str
    correct: bool
    explanation: str


class ResultsOut(BaseModel):
    attempt_id: str
    set_id: str
    key_version: str
    score: Score
    answers: dict[str, str]
    questions: list[ResultQuestion]


class TopicRefOut(BaseModel):
    id: str
    name: str


class BestScoreOut(BaseModel):
    correct: int
    total: int


class CatalogSetOut(BaseModel):
    id: str
    title: str
    topic: TopicRefOut
    published_at: str
    question_count: int
    best: BestScoreOut | None


class CatalogCourseOut(BaseModel):
    id: str
    title: str
    sets: list[CatalogSetOut]


class PracticeCatalogOut(BaseModel):
    courses: list[CatalogCourseOut]
