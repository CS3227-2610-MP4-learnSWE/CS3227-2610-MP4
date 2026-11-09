"""Request body of POST /grading-runs. Responses are plain dicts built in `queries` (the shapes are in plan.md)."""
from pydantic import BaseModel, ConfigDict


class GradingRunIn(BaseModel):
    """All three fields are required strings; unknown fields are rejected with FastAPI's standard 422."""

    model_config = ConfigDict(extra="forbid", strict=True)
    workflow: str
    period_start: str
    period_end: str
