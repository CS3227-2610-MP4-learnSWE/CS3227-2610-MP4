"""Render the `invocation-v2` Markdown report and the metrics CSV from metric rows."""

from __future__ import annotations

import csv
import io
from collections.abc import Sequence

from .invocation_metrics import UNAVAILABLE
from .mdtable import escape_cell, table

CSV_COLUMNS = [
    "record", "run_id", "invocation_id", "role", "role_label", "session_id", "agent_id", "prompt_number", "launched_by",
    "requested_agent_type", "requested_model", "observed_models", "model_match", "started_at", "finished_at", "elapsed_s",
    "active_s", "tool_time_s", "tool_calls_timed", "wait_before_start_s", "requests", "input_tokens", "cache_read_tokens",
    "cache_write_5m_tokens", "cache_write_1h_tokens", "output_tokens", "reasoning_tokens", "reasoning_share",
    "cache_hit_ratio", "zero_cache_read_after_first", "cache_writes_after_gap", "cache_write_tokens_after_gap",
    "context_first", "context_max", "context_mean", "cost_usd", "cost_input", "cost_cache_read", "cost_cache_write_5m",
    "cost_cache_write_1h", "cost_output", "tool_calls", "failed_tool_calls", "tool_calls_by_name", "files_read",
    "files_distinct", "files_repeated", "repeated_paths", "human_messages", "arm", "phase", "revision_round", "trigger",
    "start_commit", "end_commit", "agent_definition_hash", "likely_agent_inferred_guess",
]  # fmt: skip

_ONE_DECIMAL = {"elapsed_s", "active_s", "tool_time_s", "wait_before_start_s", "context_mean"}
_FOUR_DECIMALS = {"reasoning_share", "cache_hit_ratio"}
_SIX_DECIMALS = {"cost_usd", "cost_input", "cost_cache_read", "cost_cache_write_5m", "cost_cache_write_1h", "cost_output"}

# (heading before the table or None, table headers with the CSV column each shows, has a TOTAL row)
_TABLES = {
    "A": [
        ("Invocation ID", "invocation_id"), ("Role", "role"), ("Role label", "role_label"), ("Session ID", "session_id"),
        ("Agent ID", "agent_id"), ("Prompt", "prompt_number"), ("Launched by", "launched_by"),
        ("Requested agent type", "requested_agent_type"), ("Requested model", "requested_model"),
        ("Observed model(s)", "observed_models"), ("Model match", "model_match"), ("Started", "started_at"),
        ("Finished", "finished_at"), ("Elapsed (s)", "elapsed_s"), ("Requests", "requests"), ("Input", "input_tokens"),
        ("Cache read", "cache_read_tokens"), ("Cache write (5m)", "cache_write_5m_tokens"),
        ("Cache write (1h)", "cache_write_1h_tokens"), ("Output", "output_tokens"), ("Reasoning", "reasoning_tokens"),
        ("Cost (USD)", "cost_usd"),
    ],
    "B": [
        ("Invocation ID", "invocation_id"), ("Reasoning share", "reasoning_share"), ("Cache hit ratio", "cache_hit_ratio"),
        ("Zero cache read after first", "zero_cache_read_after_first"), ("Cache writes after gap", "cache_writes_after_gap"),
        ("Cache write tokens after gap", "cache_write_tokens_after_gap"), ("First context", "context_first"),
        ("Max context", "context_max"), ("Mean context", "context_mean"),
    ],
    "C": [
        ("Invocation ID", "invocation_id"), ("Tool calls", "tool_calls"), ("Failed tool calls", "failed_tool_calls"),
        ("Tool calls by name", "tool_calls_by_name"), ("Files read", "files_read"), ("Distinct files", "files_distinct"),
        ("Repeated reads", "files_repeated"), ("Human messages", "human_messages"), ("Active (s)", "active_s"),
        ("Tool time (s)", "tool_time_s"), ("Tool calls timed", "tool_calls_timed"),
        ("Wait before start (s)", "wait_before_start_s"),
    ],
    "D": [
        ("Invocation ID", "invocation_id"), ("Input", "cost_input"), ("Cache read", "cost_cache_read"),
        ("Cache write (5m)", "cost_cache_write_5m"), ("Cache write (1h)", "cost_cache_write_1h"), ("Output", "cost_output"),
        ("Total", "cost_usd"),
    ],
    "E": [
        ("Invocation ID", "invocation_id"), ("Arm", "arm"), ("Phase", "phase"), ("Revision round", "revision_round"),
        ("Trigger", "trigger"), ("Start commit", "start_commit"), ("End commit", "end_commit"),
        ("Agent definition hash", "agent_definition_hash"),
    ],
}  # fmt: skip
_SECTIONS = [
    ("## Invocations", "A"),
    ("## Cache and context", "B"),
    ("## Tools, files and time", "C"),
    ("## Cost by token type (USD)", "D"),
    ("## Metadata", "E"),
]
_INTRO = (
    "Costs are tracker list-price estimates, not billed. `unavailable` means the logs do not contain the data; no metric is "
    "estimated. The only inference is `likely_agent (inferred guess)` on the unattributed line, which is a guess and is never "
    "added to any invocation. A blank cell means not applicable. Elapsed values are wall-clock durations; the run total is "
    "latest finish minus earliest start. Wait before start is a wall-clock gap, not proof that one stage depended on another. "
    "Role is the agent type logged by Claude Code; Requested agent type is the type named in the launching Agent call; Role "
    "label is the label from the metadata file and never changes an invocation ID. Claude Code logs only; Codex sessions are "
    "not included."
)


def format_value(column: str, value: object) -> str:
    """Cell text: blank for None, `unavailable` for missing data, fixed decimals for floats."""
    if value is None:
        return ""
    if value == UNAVAILABLE:
        return UNAVAILABLE
    if isinstance(value, float):
        if column in _ONE_DECIMAL:
            return format(value, ".1f")
        if column in _FOUR_DECIMALS:
            return format(value, ".4f")
        if column in _SIX_DECIMALS:
            return format(value, ".6f")
    return str(value)


def render_csv(rows: Sequence[dict]) -> str:
    """Header then rows in the order given (invocations, total, unattributed); UTF-8 text with `\\n` endings."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for row in rows:
        writer.writerow([format_value(column, row.get(column)) for column in CSV_COLUMNS])
    return buffer.getvalue()


def render_markdown(
    run_id: str,
    session_ids: Sequence[str],
    invocation_rows: Sequence[dict],
    total: dict,
    unattributed: dict,
    likely_agent: str | None,
) -> str:
    lines = [
        f"# Invocation report: {run_id}",
        "",
        "Format: `invocation-v2`",
        "",
        f"Sessions: {', '.join(sorted(session_ids))}",
        "",
        _INTRO,
    ]
    for heading, key in _SECTIONS:
        lines += ["", heading, "", _table(key, invocation_rows, total)]
        if key == "A":
            lines += ["", _unattributed_line(unattributed, likely_agent)]
    return "\n".join(lines) + "\n"


def _table(key: str, rows: Sequence[dict], total: dict) -> str:
    columns = _TABLES[key]
    body = [[escape_cell(format_value(column, row.get(column))) for _, column in columns] for row in rows]
    if key != "E":
        cells = [escape_cell(format_value(column, total.get(column))) for _, column in columns]
        body.append(["TOTAL", *cells[1:]])
    return table([header for header, _ in columns], body)


def _unattributed_line(row: dict, likely_agent: str | None) -> str:
    fields = (
        ("requests", "requests"), ("input", "input_tokens"), ("cache_read", "cache_read_tokens"),
        ("cache_write_5m", "cache_write_5m_tokens"), ("cache_write_1h", "cache_write_1h_tokens"),
        ("output", "output_tokens"), ("reasoning", "reasoning_tokens"), ("cost_usd", "cost_usd"),
    )  # fmt: skip
    numbers = ", ".join(f"{label}={format_value(column, row.get(column))}" for label, column in fields)
    guess = escape_cell(likely_agent) if likely_agent else "none"
    return (
        f"Unattributed usage (rows in the listed sessions that no invocation claims): {numbers}; "
        f"likely_agent (inferred guess, not measured): {guess}"
    )
