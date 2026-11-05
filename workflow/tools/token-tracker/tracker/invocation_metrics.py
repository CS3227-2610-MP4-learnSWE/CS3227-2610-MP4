"""Per-invocation metrics as row dicts keyed by CSV column name.

A value of `None` is a blank cell (not applicable). `UNAVAILABLE` means the logs do not hold the data.
Nothing is estimated.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from .invocations import InvocationRecord
from .model import UsageRow
from .pricing import cost_breakdown
from .timeutil import format_utc, parse_utc

UNAVAILABLE = "unavailable"
GAP_SECONDS = 300
_TOKEN_COLUMNS = (
    ("input_tokens", "input_tokens"),
    ("cache_read_tokens", "cache_read_tokens"),
    ("cache_write_5m_tokens", "cache_write_5m_tokens"),
    ("cache_write_1h_tokens", "cache_write_1h_tokens"),
    ("output_tokens", "output_tokens"),
    ("reasoning_tokens", "reasoning_tokens"),
)
_COST_COLUMNS = (
    ("cost_input", "input"),
    ("cost_cache_read", "cache_read"),
    ("cost_cache_write_5m", "cache_write_5m"),
    ("cost_cache_write_1h", "cache_write_1h"),
    ("cost_output", "output"),
)


def metric_rows(records: Sequence[InvocationRecord], prices: dict) -> list[dict[str, object]]:
    """One row per record, in the same order."""
    rows = []
    for record in records:
        row = _identity(record)
        row.update(_models(record))
        row.update(_times(record))
        row.update(_usage(record))
        row.update(_cache(record))
        row.update(_costs(record, prices))
        row.update(_tools(record))
        rows.append(row)
    _add_waits(records, rows)
    return rows


def total_row(records: Sequence[InvocationRecord], rows: Sequence[dict], prices: dict) -> dict[str, object]:
    """The run total: sums, merges and ratios over all invocations; elapsed is latest finish minus earliest start."""
    all_rows = [usage for record in records for usage in record.rows]
    infos = [info for record in records for info in record.window.requests]
    calls = [call for record in records for call in record.window.tool_calls]
    total: dict[str, object] = {"record": "run_total", "run_id": records[0].run_id if records else None, "role": "TOTAL"}
    total["requested_model"] = _union(rows, "requested_model")
    total["observed_models"] = _union(rows, "observed_models")
    matches = [row["model_match"] for row in rows]
    total["model_match"] = "no" if "no" in matches else (UNAVAILABLE if UNAVAILABLE in matches else "yes")
    starts = [r.window.first_time for r in records if r.window.first_time]
    finishes = [r.window.last_time for r in records if r.window.last_time]
    if starts and finishes:
        total.update(started_at=format_utc(min(starts)), finished_at=format_utc(max(finishes)))
        total["elapsed_s"] = (max(finishes) - min(starts)).total_seconds()
    else:
        total.update(started_at=UNAVAILABLE, finished_at=UNAVAILABLE, elapsed_s=UNAVAILABLE)
    tool_times = [row["tool_time_s"] for row in rows]
    total["tool_time_s"] = UNAVAILABLE if UNAVAILABLE in tool_times else float(sum(tool_times))
    total["tool_calls_timed"] = sum(row["tool_calls_timed"] for row in rows)
    total.update(_sums(all_rows))
    total.update(_ratios(all_rows, infos))
    for column in ("zero_cache_read_after_first", "cache_writes_after_gap", "cache_write_tokens_after_gap"):
        total[column] = _sum_available(rows, column)
    maxima = [row["context_max"] for row in rows if row["context_max"] != UNAVAILABLE]
    total["context_max"] = max(maxima) if maxima else UNAVAILABLE
    total["context_mean"] = sum(r.prompt_tokens for r in all_rows) / len(all_rows) if all_rows else UNAVAILABLE
    for column, _ in _COST_COLUMNS + (("cost_usd", ""),):
        values = [row[column] for row in rows]
        total[column] = UNAVAILABLE if (UNAVAILABLE in values or not values) else float(sum(values))
    paths = [call.read_path for call in calls if call.read_path]
    total.update(tool_calls=len(calls), failed_tool_calls=sum(1 for call in calls if call.is_error))
    total["tool_calls_by_name"] = _names(calls)
    total.update(files_read=len(paths), files_distinct=len(set(paths)), files_repeated=len(paths) - len(set(paths)))
    total["human_messages"] = sum(record.window.human_messages for record in records)
    return total


def unattributed_row(run_id: str, rows: Sequence[UsageRow], likely_agent: str | None) -> dict[str, object]:
    """Usage rows of the listed sessions that no invocation claims; `likely_agent` is a labelled inference."""
    row: dict[str, object] = {"record": "unattributed", "run_id": run_id, "role": "UNATTRIBUTED", "requests": len(rows)}
    row.update(_sums(rows))
    row["cost_usd"] = UNAVAILABLE if any(r.cost_usd is None for r in rows) else float(sum(r.cost_usd for r in rows))
    row["likely_agent_inferred_guess"] = likely_agent
    return row


def _identity(record: InvocationRecord) -> dict[str, object]:
    orchestrator = record.prompt_number is None
    return {
        "record": "invocation",
        "run_id": record.run_id,
        "invocation_id": record.invocation_id,
        "role": record.role,
        "session_id": record.session_id,
        "agent_id": record.agent_id or None,
        "prompt_number": record.prompt_number,
        "launched_by": None if orchestrator else (record.launched_by or UNAVAILABLE),
        "requested_agent_type": None if orchestrator else (record.requested_agent_type or UNAVAILABLE),
    }


def _models(record: InvocationRecord) -> dict[str, object]:
    infos = record.window.requests
    requested = sorted({info.requested_model for info in infos if info.requested_model})
    observed = sorted({info.row.model for info in infos})
    with_request = [info for info in infos if info.requested_model]
    if not with_request:
        match = UNAVAILABLE
    else:
        match = "no" if any(info.requested_model != info.row.model for info in with_request) else "yes"
    return {
        "requested_model": "; ".join(requested) if requested else UNAVAILABLE,
        "observed_models": "; ".join(observed) if observed else UNAVAILABLE,
        "model_match": match,
    }


def _times(record: InvocationRecord) -> dict[str, object]:
    window = record.window
    first, last = window.first_time, window.last_time
    stamps = [t for t in (parse_utc(r.timestamp) for r in record.rows) if t is not None]
    timed = [
        (call.result_time - call.use_time).total_seconds()
        for call in window.tool_calls
        if call.use_time and call.result_time and call.result_time >= call.use_time
    ]
    return {
        "started_at": format_utc(first) if first else UNAVAILABLE,
        "finished_at": format_utc(last) if last else UNAVAILABLE,
        "elapsed_s": (last - first).total_seconds() if first and last else UNAVAILABLE,
        "active_s": (max(stamps) - min(stamps)).total_seconds() if stamps else UNAVAILABLE,
        "tool_time_s": UNAVAILABLE if window.tool_calls and not timed else float(sum(timed)),
        "tool_calls_timed": len(timed),
        "human_messages": window.human_messages,
    }


def _usage(record: InvocationRecord) -> dict[str, object]:
    row = _sums(record.rows)
    row.update(_ratios(record.rows, record.window.requests))
    return row


def _sums(rows: Sequence[UsageRow]) -> dict[str, object]:
    result: dict[str, object] = {"requests": len(rows)}
    for column, field in _TOKEN_COLUMNS:
        result[column] = sum(getattr(r, field) for r in rows)
    return result


def _ratios(rows: Sequence[UsageRow], infos) -> dict[str, object]:
    """Reasoning share over requests that report thinking tokens; cache hit ratio over all prompt tokens."""
    reported = [info.row for info in infos if info.reasoning_reported]
    output = sum(r.output_tokens for r in reported)
    prompt = sum(r.prompt_tokens for r in rows)
    return {
        "reasoning_share": sum(r.reasoning_tokens for r in reported) / output if output else UNAVAILABLE,
        "cache_hit_ratio": sum(r.cache_read_tokens for r in rows) / prompt if prompt else UNAVAILABLE,
    }


def _cache(record: InvocationRecord) -> dict[str, object]:
    rows = record.rows
    sizes = [r.prompt_tokens for r in rows]
    result: dict[str, object] = {
        "zero_cache_read_after_first": sum(1 for r in rows[1:] if r.cache_read_tokens == 0) if rows else UNAVAILABLE,
        "context_first": sizes[0] if sizes else UNAVAILABLE,
        "context_max": max(sizes) if sizes else UNAVAILABLE,
        "context_mean": sum(sizes) / len(sizes) if sizes else UNAVAILABLE,
    }
    count = tokens = pairs = 0
    for earlier, later in zip(rows, rows[1:]):
        a, b = parse_utc(earlier.timestamp), parse_utc(later.timestamp)
        if a is None or b is None:
            continue
        pairs += 1
        writes = later.cache_write_5m_tokens + later.cache_write_1h_tokens
        if (b - a).total_seconds() > GAP_SECONDS and writes > 0:
            count, tokens = count + 1, tokens + writes
    unknown = not rows or (len(rows) >= 2 and pairs == 0)
    result["cache_writes_after_gap"] = UNAVAILABLE if unknown else count
    result["cache_write_tokens_after_gap"] = UNAVAILABLE if unknown else tokens
    return result


def _costs(record: InvocationRecord, prices: dict) -> dict[str, object]:
    parts = [cost_breakdown(r, prices) for r in record.rows]
    if not parts or any(p is None for p in parts):
        return {column: UNAVAILABLE for column, _ in _COST_COLUMNS} | {"cost_usd": UNAVAILABLE}
    result: dict[str, object] = {}
    for column, key in _COST_COLUMNS:
        total = 0.0
        for p in parts:
            total += p[key]
        result[column] = total
    cost = 0.0
    for r in record.rows:
        cost += r.cost_usd
    result["cost_usd"] = cost
    return result


def _tools(record: InvocationRecord) -> dict[str, object]:
    calls = record.window.tool_calls
    paths = [call.read_path for call in calls if call.read_path]
    repeated = sorted(path for path, count in Counter(paths).items() if count > 1)
    return {
        "tool_calls": len(calls),
        "failed_tool_calls": sum(1 for call in calls if call.is_error),
        "tool_calls_by_name": _names(calls),
        "files_read": len(paths),
        "files_distinct": len(set(paths)),
        "files_repeated": len(paths) - len(set(paths)),
        "repeated_paths": "; ".join(repeated),
    }


def _names(calls) -> str:
    counts = Counter(call.name for call in calls)
    return "; ".join(f"{name}={counts[name]}" for name in sorted(counts)) or "none"


def _add_waits(records: Sequence[InvocationRecord], rows: list[dict]) -> None:
    """Start minus the latest finish among the other invocations that finished at or before this start."""
    for i, (record, row) in enumerate(zip(records, rows)):
        start = record.window.first_time
        finishes = [
            other.window.last_time
            for j, other in enumerate(records)
            if j != i and other.window.last_time is not None and start is not None and other.window.last_time <= start
        ]
        row["wait_before_start_s"] = (start - max(finishes)).total_seconds() if finishes else UNAVAILABLE


def _union(rows: Sequence[dict], column: str) -> str:
    values = {part for row in rows if row[column] != UNAVAILABLE for part in str(row[column]).split("; ")}
    return "; ".join(sorted(values)) if values else UNAVAILABLE


def _sum_available(rows: Sequence[dict], column: str) -> object:
    values = [row[column] for row in rows if row[column] != UNAVAILABLE]
    return sum(values) if values else UNAVAILABLE
