"""Check that invocation rows plus unattributed rows reproduce what the existing `report` code path sees."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence

from .errors import TrackerError
from .model import UsageRow
from .report import summarise

_INT_QUANTITIES = (
    "requests",
    "input_tokens",
    "cache_read_tokens",
    "cache_write_5m_tokens",
    "cache_write_1h_tokens",
    "output_tokens",
    "reasoning_tokens",
)
_DIFFERENCE = "difference (report minus invocations plus unattributed)"
_DUPLICATE_CAUSE = (
    "a message ID is logged in more than one file for these sessions (for example a copy of a log outside the session "
    "folder layout) with a larger output_tokens, so the report keeps a different line than the invocation reader"
)
_PARSING_CAUSE = (
    "a log line is counted differently by the invocation reader and by the report (a parsing difference); "
    "treat this as a tracker defect"
)


def cross_check(
    invocation_rows: Sequence[UsageRow], report_rows: Sequence[UsageRow], session_ids: Sequence[str]
) -> list[UsageRow]:
    """The report rows no invocation claims, or a TrackerError (exit code 1) if the two views disagree."""
    remaining = Counter(invocation_rows)
    unattributed = []
    for row in report_rows:
        if remaining[row] > 0:
            remaining[row] -= 1
        else:
            unattributed.append(row)
    missing = [row for row, count in remaining.items() for _ in range(count)]

    lines = _quantity_lines(invocation_rows, unattributed, report_rows)
    if not missing and not lines:
        return unattributed
    prefix = f"cross-check failed for session(s) {', '.join(sorted(session_ids))}: "
    out = []
    if missing:
        sources = sorted({f"{row.session_id}/{row.agent_id or 'main'}" for row in missing})
        out.append(
            prefix
            + f"{len(missing)} invocation request(s) have no identical row in the report "
            f"(affected sources: {', '.join(sources)}); report rows: {len(report_rows)}, "
            f"invocation rows plus unattributed rows: {len(invocation_rows) + len(unattributed)}"
        )
    out.extend(prefix + line for line in lines)
    out.append(prefix + "likely cause: " + (_DUPLICATE_CAUSE if missing else _PARSING_CAUSE))
    raise TrackerError("\n".join(out), exit_code=1)


def _quantity_lines(invocation_rows, unattributed, report_rows) -> list[str]:
    own, stray, report = (summarise(list(rows))[-1] for rows in (invocation_rows, unattributed, report_rows))
    lines = []
    for quantity in _INT_QUANTITIES:
        a, b = own[quantity] + stray[quantity], report[quantity]
        if a != b:
            lines.append(f"{quantity}: invocations plus unattributed = {a}, report = {b}, {_DIFFERENCE} = {b - a:+d}")
    a = None if own["cost_usd"] is None or stray["cost_usd"] is None else own["cost_usd"] + stray["cost_usd"]
    b = report["cost_usd"]
    if (a is None) != (b is None) or (a is not None and not math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)):
        difference = "unavailable" if a is None or b is None else f"{b - a:+.6f}"
        lines.append(f"cost_usd: invocations plus unattributed = {_usd(a)}, report = {_usd(b)}, {_DIFFERENCE} = {difference}")
    return lines


def _usd(value: float | None) -> str:
    return "unavailable" if value is None else f"{value:.6f}"
