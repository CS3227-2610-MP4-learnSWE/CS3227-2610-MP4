"""Request and response schemas for the practice attempt API."""
from typing import Literal

from pydantic import BaseModel


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


class AttemptOut(BaseModel):
    attempt_id: str
    set_id: str
    status: Literal["in_progress", "submitted"]
    answers: dict[str, str]


class AnswersIn(BaseModel):
    answers: dict[str, str]


class AnswersSavedOut(BaseModel):
    attempt_id: str
    status: Literal["in_progress"]
    answers: dict[str, str]


class Score(BaseModel):
    correct: int
    total: int


class SubmitOut(BaseModel):
    attempt_id: str
    status: Literal["submitted"]
    score: Score


class QuestionResult(BaseModel):
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
    questions: list[QuestionResult]
