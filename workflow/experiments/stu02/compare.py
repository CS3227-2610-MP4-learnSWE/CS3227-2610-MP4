"""Side-by-side comparison of token usage, cost and grader score for the three runs.

Usage (from the repo root), after each run has been graded with grade_run.py:
    python workflow/experiments/stu02/compare.py

Reads token usage from the local Claude logs through the token tracker, the grader
results in workflow/experiments/results/stu02-<label>-grade.json, and optional
hand-recorded facts in stu02-<label>-notes.json, for example:
    {"revision_rounds": 1, "review_minutes": 25, "quality_score": 4}
Prints the table and writes stu02-comparison.csv, .md and .html (open the .html in a
browser). It is regenerated from the latest logs and grade files on every run.
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "workflow" / "tools" / "token-tracker"))

from tracker.export import collect_rows  # noqa: E402
from tracker.pricing import load_prices  # noqa: E402
from tracker.report import summarise  # noqa: E402

from html_report import agent_costs, bucket_costs, render_html  # noqa: E402

RESULTS = REPO / "workflow" / "experiments" / "results"
# The branches the run sessions actually worked on (each session names its own worktree branch).
RUNS = [
    ("A", "claude/stu02-run-a-eba95d"),
    ("B", "claude/stu02-run-b-223ec1"),
    ("baseline", "claude/stu02-run-baseline-e1c0af"),
]
COLUMNS = [
    "run", "grader_passed", "grader_total", "grader_pct", "own_tests_passed", "own_tests_total",
    "requests", "input_tokens", "cache_read_tokens", "cache_write_tokens", "output_tokens",
    "reasoning_tokens", "total_tokens", "cost_usd", "cost_per_grader_pass_usd",
    "revision_rounds", "review_minutes", "quality_score",
]


def build_row(label: str, total: dict, grade: dict | None, notes: dict) -> dict:
    """One comparison row from a run's tracker TOTAL, grade result and notes."""
    grader = (grade or {}).get("grader", {})
    own = (grade or {}).get("own_tests", {})
    write = total["cache_write_5m_tokens"] + total["cache_write_1h_tokens"]
    passed, count = grader.get("passed"), grader.get("total")
    cost = total["cost_usd"]
    per_pass = cost / passed if cost is not None and passed else None
    return {
        "run": label,
        "grader_passed": passed, "grader_total": count,
        "grader_pct": round(100 * passed / count, 1) if passed is not None and count else None,
        "own_tests_passed": own.get("passed"), "own_tests_total": own.get("total"),
        "requests": total["requests"],
        "input_tokens": total["input_tokens"], "cache_read_tokens": total["cache_read_tokens"],
        "cache_write_tokens": write, "output_tokens": total["output_tokens"],
        "reasoning_tokens": total["reasoning_tokens"],
        "total_tokens": total["input_tokens"] + total["cache_read_tokens"] + write + total["output_tokens"],
        "cost_usd": cost, "cost_per_grader_pass_usd": per_pass,
        "revision_rounds": notes.get("revision_rounds"),
        "review_minutes": notes.get("review_minutes"),
        "quality_score": notes.get("quality_score"),
    }


def cell(value) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4f}" if abs(value) < 100 else f"{value:.1f}"
    return f"{value:,}" if isinstance(value, int) else str(value)


def render_markdown(rows: list[dict]) -> str:
    lines = ["| " + " | ".join(COLUMNS) + " |", "|" + "---|" * len(COLUMNS)]
    lines += ["| " + " | ".join(cell(r[c]) for c in COLUMNS) + " |" for r in rows]
    return "\n".join(lines)


def run_rows(rows: list, branch: str) -> list:
    """All requests of every session that worked on the run branch.

    Subagents share their parent's session id, so a subagent working in its own
    worktree (and logging a different branch) still counts toward the run. This
    relies on each run having its own fresh session.
    """
    sessions = {r.session_id for r in rows if r.branch == branch}
    return [r for r in rows if r.session_id in sessions]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def main() -> int:
    prices = load_prices(REPO / "workflow" / "tools" / "token-tracker" / "prices.json")
    all_rows = collect_rows(Path.home() / ".claude", Path.home() / ".codex", prices)
    table, buckets, agents = [], {}, {}
    for label, branch in RUNS:
        rows = run_rows(all_rows, branch)
        summary = summarise(rows)
        table.append(build_row(label, summary[-1], load_json(RESULTS / f"stu02-{label}-grade.json") or None,
                               load_json(RESULTS / f"stu02-{label}-notes.json")))
        buckets[label] = bucket_costs(rows, prices)
        agents[label] = agent_costs(summary[:-1])
    RESULTS.mkdir(parents=True, exist_ok=True)
    with (RESULTS / "stu02-comparison.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in table:
            writer.writerow({c: "" if row[c] is None else row[c] for c in COLUMNS})
    markdown = render_markdown(table)
    (RESULTS / "stu02-comparison.md").write_text(markdown + "\n", encoding="utf-8")
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    (RESULTS / "stu02-comparison.html").write_text(render_html(table, buckets, agents, stamp), encoding="utf-8")
    print(markdown)
    print(f"\nWrote stu02-comparison.csv, .md and .html in {RESULTS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
