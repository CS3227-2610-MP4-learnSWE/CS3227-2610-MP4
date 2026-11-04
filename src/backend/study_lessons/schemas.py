"""Response models and the strict request body for the study endpoints."""
from pydantic import BaseModel, ConfigDict, StrictBool


class CompletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    completed: StrictBool


class CourseCountsOut(BaseModel):
    lesson_count: int
    completed_count: int


class CourseSummary(CourseCountsOut):
    id: str
    title: str


class CourseListOut(BaseModel):
    courses: list[CourseSummary]
    totals: CourseCountsOut


class CourseRef(BaseModel):
    id: str
    title: str


class LessonSummary(BaseModel):
    id: str
    title: str
    excerpt: str
    completed: bool


class TopicGroup(BaseModel):
    id: str | None
    name: str
    lessons: list[LessonSummary]


class LessonListOut(BaseModel):
    course: CourseRef
    topics: list[TopicGroup]


class TopicRef(BaseModel):
    id: str | None
    name: str


class LessonOut(BaseModel):
    id: str
    course: CourseRef
    topic: TopicRef
    title: str
    content: str
    published_at: str
    completed: bool
    completed_at: str | None


class CompletionCourse(CourseCountsOut):
    id: str


class CompletionOut(BaseModel):
    lesson_id: str
    completed: bool
    completed_at: str | None
    course: CompletionCourse
