"""A labelled guess of which invocation most likely made usage that no invocation claims.

The guess uses only the row's session ID and timestamp and the invocations' start and finish times.
It is an inference, shown on the unattributed line only, and is never added to any invocation.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from .invocations import InvocationRecord
from .model import UsageRow
from .timeutil import parse_utc

NONE_GUESS = "unavailable"


def likely_agent_text(rows: Sequence[UsageRow], records: Sequence[InvocationRecord]) -> str | None:
    """`id (rule: window; requests: k)` entries joined by `; `, or None when there are no unattributed rows."""
    if not rows:
        return None
    guesses: Counter = Counter(_guess(row, records) for row in rows)
    ordered = sorted(guesses, key=lambda g: (g[0] == NONE_GUESS, g[0], g[1]))
    return "; ".join(f"{name} (rule: {rule}; requests: {guesses[(name, rule)]})" for name, rule in ordered)


def _guess(row: UsageRow, records: Sequence[InvocationRecord]) -> tuple[str, str]:
    moment = parse_utc(row.timestamp)
    candidates = [
        (position, record)
        for position, record in enumerate(records)
        if record.session_id == row.session_id and record.window.first_time and record.window.last_time
    ]
    if moment is None or not candidates:
        return NONE_GUESS, "none"
    inside = [
        (position, record)
        for position, record in candidates
        if record.window.first_time <= moment <= record.window.last_time
    ]
    if inside:
        length = lambda item: ((item[1].window.last_time - item[1].window.first_time).total_seconds(), item[0])
        return min(inside, key=length)[1].invocation_id, "window"
    distance = lambda item: (
        min(abs((moment - item[1].window.first_time).total_seconds()), abs((moment - item[1].window.last_time).total_seconds())),
        item[0],
    )
    return min(candidates, key=distance)[1].invocation_id, "nearest"
