"""ADM-01 feature analytics: the recording hooks used by the companion, practice and TEA-02 routes."""
from feature_analytics.grading_text import GradingContent, format_mcq_batch_for_grading
from feature_analytics.recording import (
    record_chat_request_outcome,
    record_chat_request_received,
    record_generation_accepted,
    record_generation_outcome,
    record_practice_attempt_started,
    record_practice_attempt_submitted,
)

__all__ = [
    "GradingContent",
    "format_mcq_batch_for_grading",
    "record_chat_request_outcome",
    "record_chat_request_received",
    "record_generation_accepted",
    "record_generation_outcome",
    "record_practice_attempt_started",
    "record_practice_attempt_submitted",
]
