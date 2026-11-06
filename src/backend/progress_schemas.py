"""Response models for GET /api/progress. Scores and counts only; no answer data."""
from pydantic import BaseModel

from progress_rules import TopicStatus


class LessonTotals(BaseModel):
    lesson_count: int
    completed_count: int


class CourseProgress(BaseModel):
    id: str
    title: str
    lesson_count: int
    completed_count: int


class RecentLesson(BaseModel):
    lesson_id: str
    course_id: str
    title: str
    completed_at: str


class LessonProgress(BaseModel):
    totals: LessonTotals
    courses: list[CourseProgress]
    recent: list[RecentLesson]


class ScoreCount(BaseModel):
    correct: int
    total: int


class LatestScore(ScoreCount):
    submitted_at: str


class SetProgress(BaseModel):
    set_id: str
    title: str
    attempts_submitted: int
    best: ScoreCount
    latest: LatestScore


class PracticeProgress(BaseModel):
    sets: list[SetProgress]
    average_latest_percent: int | None


class TopicRef(BaseModel):
    id: str | None
    name: str


class TopicItem(BaseModel):
    topic: TopicRef
    answered: int
    correct: int
    accuracy_percent: int
    status: TopicStatus


class TopicRule(BaseModel):
    min_answers: int
    weak_below_percent: int


class TopicProgress(BaseModel):
    rule: TopicRule
    items: list[TopicItem]


class ProgressOut(BaseModel):
    lessons: LessonProgress
    practice: PracticeProgress
    topics: TopicProgress
