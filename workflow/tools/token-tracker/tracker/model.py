"""The row shared by every parser, exporter and report."""

from __future__ import annotations

from dataclasses import asdict, dataclass

COLUMNS = [
    "tool",
    "session_id",
    "agent_id",
    "agent_type",
    "is_subagent",
    "model",
    "branch",
    "cwd",
    "timestamp",
    "input_tokens",
    "cache_read_tokens",
    "cache_write_5m_tokens",
    "cache_write_1h_tokens",
    "output_tokens",
    "reasoning_tokens",
    "cost_usd",
]


@dataclass(frozen=True)
class UsageRow:
    """One model request. `reasoning_tokens` is a subset of `output_tokens`."""

    tool: str
    session_id: str
    agent_id: str
    agent_type: str
    is_subagent: bool
    model: str
    branch: str
    cwd: str
    timestamp: str
    input_tokens: int
    cache_read_tokens: int
    cache_write_5m_tokens: int
    cache_write_1h_tokens: int
    output_tokens: int
    reasoning_tokens: int
    cost_usd: float | None = None

    def as_csv_dict(self) -> dict:
        data = asdict(self)
        data["is_subagent"] = "true" if self.is_subagent else "false"
        data["cost_usd"] = "" if self.cost_usd is None else f"{self.cost_usd:.6f}"
        return data
