"""Summarise rows by agent type and model."""

from __future__ import annotations

import csv
from pathlib import Path

from .model import UsageRow

SUMMARY_COLUMNS = [
    "agent_type",
    "model",
    "requests",
    "input_tokens",
    "cache_read_tokens",
    "cache_write_5m_tokens",
    "cache_write_1h_tokens",
    "output_tokens",
    "reasoning_tokens",
    "cost_usd",
]
_SUMS = SUMMARY_COLUMNS[3:9]


def summarise(rows: list[UsageRow], branch: str | None = None) -> list[dict]:
    """Groups sorted by agent type and model, then a TOTAL row.

    A group's cost is None if any of its requests could not be priced.
    """
    if branch:
        rows = [r for r in rows if r.branch == branch]
    groups: dict[tuple, list[UsageRow]] = {}
    for row in rows:
        groups.setdefault((row.agent_type, row.model), []).append(row)
    summary = [_group(agent, model, members) for (agent, model), members in sorted(groups.items())]
    summary.append(_group("TOTAL", "", rows))
    return summary


def _group(agent_type: str, model: str, rows: list[UsageRow]) -> dict:
    group = {"agent_type": agent_type, "model": model, "requests": len(rows)}
    for field in _SUMS:
        group[field] = sum(getattr(r, field) for r in rows)
    costs = [r.cost_usd for r in rows]
    group["cost_usd"] = None if any(c is None for c in costs) else sum(costs)
    return group


def render_table(summary: list[dict]) -> str:
    cells = [SUMMARY_COLUMNS] + [[_cell(g[c]) for c in SUMMARY_COLUMNS] for g in summary]
    widths = [max(len(row[i]) for row in cells) for i in range(len(SUMMARY_COLUMNS))]
    lines = ["  ".join(value.ljust(widths[i]) for i, value in enumerate(row)).rstrip() for row in cells]
    return "\n".join(lines)


def write_summary_csv(summary: list[dict], path: Path) -> None:
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for group in summary:
            writer.writerow({c: _cell(group[c]) for c in SUMMARY_COLUMNS})


def _cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)
