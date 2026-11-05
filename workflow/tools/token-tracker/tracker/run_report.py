"""Build one Markdown usage report for a feature run."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .model import UsageRow

MANIFEST_COLUMNS = [
    "feature_run_id",
    "invocation_id",
    "role",
    "effort",
    "tool",
    "session_id",
    "agent_id",
    "started_at",
    "finished_at",
]

REPORT_COLUMNS = [
    "Record",
    "Feature run ID",
    "Invocation ID",
    "Role",
    "Model(s)",
    "Effort",
    "Elapsed",
    "Requests",
    "Input",
    "Cache read",
    "Cache write (5m)",
    "Cache write (1h)",
    "Output",
    "Reasoning",
    "Cost (USD)",
]

_TOKEN_FIELDS = (
    "input_tokens",
    "cache_read_tokens",
    "cache_write_5m_tokens",
    "cache_write_1h_tokens",
    "output_tokens",
    "reasoning_tokens",
)


class ManifestError(ValueError):
    """The invocation manifest is invalid."""


class AttributionError(ValueError):
    """A usage row for a listed log source cannot be assigned exactly once."""


@dataclass(frozen=True)
class Invocation:
    feature_run_id: str
    invocation_id: str
    role: str
    effort: str
    tool: str
    session_id: str
    agent_id: str
    started_at: datetime
    finished_at: datetime


def read_manifest(path: Path) -> tuple[str, list[Invocation]]:
    """Read and validate a single-feature-run invocation CSV."""
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != MANIFEST_COLUMNS:
            raise ManifestError(f"manifest columns must be: {', '.join(MANIFEST_COLUMNS)}")
        rows = list(reader)

    if not rows:
        raise ManifestError("manifest must contain at least one invocation")

    invocations: list[Invocation] = []
    run_ids: set[str] = set()
    invocation_ids: set[str] = set()
    for line_number, row in enumerate(rows, start=2):
        if None in row:
            raise ManifestError(f"line {line_number}: too many CSV fields")
        values = {key: (value or "").strip() for key, value in row.items()}
        feature_run_id = values["feature_run_id"]
        invocation_id = values["invocation_id"]
        role = values["role"]
        effort = values["effort"]
        tool = values["tool"].lower()
        session_id = values["session_id"]
        agent_id = values["agent_id"]

        invocation_prefix = f"{feature_run_id}-{role}-"
        sequence = invocation_id[len(invocation_prefix) :] if invocation_id.startswith(invocation_prefix) else ""
        if not feature_run_id or not role or not sequence.isdigit():
            raise ManifestError(f"line {line_number}: invocation_id must be <feature_run_id>-<role>-<numeric-sequence>")
        if invocation_id in invocation_ids:
            raise ManifestError(f"line {line_number}: duplicate invocation_id {invocation_id}")
        if not role or not effort or not session_id:
            raise ManifestError(f"line {line_number}: role, effort and session_id are required")
        if tool not in {"claude", "codex"}:
            raise ManifestError(f"line {line_number}: tool must be claude or codex")

        started_at = _parse_timestamp(values["started_at"], line_number, "started_at")
        finished_at = _parse_timestamp(values["finished_at"], line_number, "finished_at")
        if finished_at < started_at:
            raise ManifestError(f"line {line_number}: finished_at is before started_at")

        invocation_ids.add(invocation_id)
        run_ids.add(feature_run_id)
        invocations.append(
            Invocation(
                feature_run_id,
                invocation_id,
                role,
                effort,
                tool,
                session_id,
                agent_id,
                started_at,
                finished_at,
            )
        )

    if len(run_ids) != 1:
        raise ManifestError("manifest must contain exactly one feature_run_id")
    feature_run_id = next(iter(run_ids))
    if Path(path).parent.name != feature_run_id:
        raise ManifestError("manifest must be inside a folder named for its feature_run_id")
    return feature_run_id, invocations


def render_report(feature_run_id: str, invocations: list[Invocation], rows: list[UsageRow]) -> str:
    """Attribute usage rows and render a deterministic feature-run Markdown report."""
    if not invocations or any(item.feature_run_id != feature_run_id for item in invocations):
        raise ManifestError("invocations must belong to the requested feature_run_id")

    by_source: dict[tuple[str, str, str], list[Invocation]] = {}
    for invocation in invocations:
        key = (invocation.tool, invocation.session_id, invocation.agent_id)
        by_source.setdefault(key, []).append(invocation)

    usage_by_invocation: dict[str, list[UsageRow]] = {item.invocation_id: [] for item in invocations}
    for row in rows:
        key = (row.tool, row.session_id, row.agent_id)
        candidates = by_source.get(key)
        if not candidates:
            continue  # The local log export also contains unrelated sessions.
        timestamp = _row_timestamp(row)
        matches = [item for item in candidates if item.started_at <= timestamp <= item.finished_at]
        if len(matches) != 1:
            reason = "outside its time range" if not matches else "matches multiple invocations"
            raise AttributionError(
                f"usage row for {row.tool}/{row.session_id}/{row.agent_id} at {row.timestamp} {reason}"
            )
        usage_by_invocation[matches[0].invocation_id].append(row)

    summaries = [_summarise_invocation(item, usage_by_invocation[item.invocation_id]) for item in invocations]
    total = _summarise_run(feature_run_id, invocations, summaries)

    lines = [
        f"# Feature-run report: {_cell(feature_run_id)}",
        "",
        "Format: `invocation-v1`",
        "",
        "Elapsed values are wall-clock durations. The run total is latest finish minus earliest start, so parallel agent time is not added twice.",
        "",
        _markdown_table([*summaries, total]),
    ]
    no_usage = [item.invocation_id for item in invocations if not usage_by_invocation[item.invocation_id]]
    if no_usage:
        lines.extend(
            [
                "",
                "No usage records matched these invocations; verify the source IDs or confirm that they made no model calls: "
                + ", ".join(_cell(item) for item in no_usage)
                + ".",
            ]
        )
    lines.append("")
    return "\n".join(lines)


def write_report(report: str, path: Path) -> None:
    """Write a complete report as UTF-8 after validation/rendering has succeeded."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8", newline="\n")


def _parse_timestamp(value: str, line_number: int, field: str) -> datetime:
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ManifestError(f"line {line_number}: {field} must be a timezone-aware ISO timestamp") from exc
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ManifestError(f"line {line_number}: {field} must include a timezone")
    return timestamp.astimezone(timezone.utc)


def _row_timestamp(row: UsageRow) -> datetime:
    try:
        timestamp = datetime.fromisoformat(row.timestamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AttributionError(f"usage row has an invalid timestamp: {row.timestamp!r}") from exc
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise AttributionError(f"usage row timestamp has no timezone: {row.timestamp!r}")
    return timestamp.astimezone(timezone.utc)


def _summarise_invocation(invocation: Invocation, rows: list[UsageRow]) -> dict:
    result = {
        "Record": "invocation",
        "Feature run ID": invocation.feature_run_id,
        "Invocation ID": invocation.invocation_id,
        "Role": invocation.role,
        "Model(s)": "; ".join(sorted({row.model for row in rows if row.model})),
        "Effort": invocation.effort,
        "Elapsed": _duration(invocation.finished_at - invocation.started_at),
        "Requests": len(rows),
        "Cost (USD)": _cost(rows),
    }
    for field, column in zip(_TOKEN_FIELDS, REPORT_COLUMNS[8:14]):
        result[column] = sum(getattr(row, field) for row in rows)
    return result


def _summarise_run(feature_run_id: str, invocations: list[Invocation], summaries: list[dict]) -> dict:
    result = {
        "Record": "feature_run_total",
        "Feature run ID": feature_run_id,
        "Invocation ID": "",
        "Role": "TOTAL",
        "Model(s)": "; ".join(sorted({model for row in summaries for model in row["Model(s)"].split("; ") if model})),
        "Effort": "",
        "Elapsed": _duration(max(item.finished_at for item in invocations) - min(item.started_at for item in invocations)),
        "Requests": sum(row["Requests"] for row in summaries),
        "Cost (USD)": None if any(row["Cost (USD)"] is None for row in summaries) else sum(row["Cost (USD)"] for row in summaries),
    }
    for column in REPORT_COLUMNS[8:14]:
        result[column] = sum(row[column] for row in summaries)
    return result


def _cost(rows: list[UsageRow]) -> float | None:
    if any(row.cost_usd is None for row in rows):
        return None
    return sum(row.cost_usd for row in rows if row.cost_usd is not None)


def _duration(duration: timedelta) -> str:
    return str(timedelta(seconds=int(duration.total_seconds())))


def _markdown_table(rows: list[dict]) -> str:
    lines = ["| " + " | ".join(REPORT_COLUMNS) + " |", "| " + " | ".join("---" for _ in REPORT_COLUMNS) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(_cell(row.get(column, "")) for column in REPORT_COLUMNS) + " |")
    return "\n".join(lines)


def _cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        value = f"{value:.6f}"
    return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("\r\n", "\n").replace("\n", "<br>")
