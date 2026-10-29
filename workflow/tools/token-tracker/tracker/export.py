"""Collect rows from both tools, filter them and write the row-level CSV."""

from __future__ import annotations

import csv
from dataclasses import replace
from pathlib import Path

from .claude_logs import read_claude_rows
from .codex_logs import read_codex_rows
from .model import COLUMNS, UsageRow
from .pricing import cost_usd


def collect_rows(
    claude_dir: Path,
    codex_dir: Path,
    prices: dict,
    cwd_contains: str | None = None,
    since: str | None = None,
) -> list[UsageRow]:
    rows = read_claude_rows(claude_dir) + read_codex_rows(codex_dir)
    if cwd_contains:
        rows = [r for r in rows if cwd_contains in r.cwd]
    if since:
        rows = [r for r in rows if r.timestamp >= since]
    rows = [replace(r, cost_usd=cost_usd(r, prices)) for r in rows]
    return sorted(rows, key=_sort_key)


def write_csv(rows: list[UsageRow], path: Path) -> None:
    """Rewrite the whole file; the same rows always give the same bytes."""
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row.as_csv_dict())


def _sort_key(row: UsageRow) -> tuple:
    return (
        row.timestamp,
        row.tool,
        row.session_id,
        row.agent_id,
        row.model,
        row.input_tokens,
        row.output_tokens,
        row.cache_read_tokens,
    )
