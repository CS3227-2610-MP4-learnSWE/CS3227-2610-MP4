"""Narrow adapter used by the shared transport; content is never passed here."""
from uuid import UUID

from ai_usage import service


class DatabaseAttemptObserver:
    def reserve(self, feature: str) -> UUID:
        return service.reserve_attempt(feature)

    def finish(self, attempt_id: UUID, outcome: str, *, input_tokens=None, output_tokens=None, total_tokens=None) -> bool:
        return service.finish_attempt(attempt_id, outcome, input_tokens=input_tokens,
                                      output_tokens=output_tokens, total_tokens=total_tokens)
