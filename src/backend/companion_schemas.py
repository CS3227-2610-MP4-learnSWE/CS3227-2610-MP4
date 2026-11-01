"""Request and response models for the companion endpoint.

Lengths and roles are checked in companion_service so each failure has its own error code
and the documented check order holds (a model that rejected them here would answer first).
"""
from typing import Literal

from pydantic import BaseModel, Field


class HistoryItem(BaseModel):
    role: str
    text: str


class ContextIn(BaseModel):
    page: Literal["practice", "other"]
    set_id: str | None = None
    attempt_id: str | None = None
    label: str | None = None


class CompanionMessageIn(BaseModel):
    message: str
    history: list[HistoryItem] = Field(default_factory=list)
    context: ContextIn


class CompanionReplyOut(BaseModel):
    reply: str
    mode: Literal["hint", "explain", "help"]
    withheld: bool
