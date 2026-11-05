"""Command line: `export` writes row-level usage, `report` summarises it."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .crosscheck import cross_check
from .errors import TrackerError
from .export import collect_rows, write_csv
from .invocation_meta import apply_metadata, read_metadata
from .invocation_metrics import metric_rows, total_row, unattributed_row
from .invocation_render import render_csv, render_markdown
from .invocations import build_invocations
from .pricing import load_prices
from .report import render_table, summarise, write_summary_csv
from .run_report import AttributionError, ManifestError, read_manifest, render_report, write_report
from .unattributed import likely_agent_text

TOOL_DIR = Path(__file__).resolve().parent.parent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tracker", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (("export", "write row-level usage CSV"), ("report", "summarise usage")):
        cmd = sub.add_parser(name, help=help_text)
        cmd.add_argument("--claude-dir", type=Path, default=Path.home() / ".claude")
        cmd.add_argument("--codex-dir", type=Path, default=Path.home() / ".codex")
        cmd.add_argument("--prices", type=Path, default=TOOL_DIR / "prices.json")
        cmd.add_argument("--cwd-contains", help="keep sessions whose working directory contains this text")
        cmd.add_argument("--since", help="keep requests at or after this ISO date or time")
        if name == "export":
            cmd.add_argument("--out", type=Path, default=Path("usage.csv"))
        else:
            cmd.add_argument("--branch", help="keep requests made on this git branch")
            cmd.add_argument("--out", type=Path, help="also write the summary as CSV")
    run_report = sub.add_parser("run-report", help="write a Markdown report for one feature run")
    run_report.add_argument("--manifest", type=Path, required=True)
    run_report.add_argument("--claude-dir", type=Path, default=Path.home() / ".claude")
    run_report.add_argument("--codex-dir", type=Path, default=Path.home() / ".codex")
    run_report.add_argument("--prices", type=Path, default=TOOL_DIR / "prices.json")
    run_report.add_argument("--out", type=Path, help="report path (default: report.md next to the manifest)")
    inv = sub.add_parser("invocations-from-logs", help="rebuild invocations and metrics from Claude Code session logs")
    inv.add_argument("--run-id", required=True)
    inv.add_argument("--meta", type=Path, help="optional metadata CSV keyed by invocation ID")
    inv.add_argument("--claude-dir", type=Path, default=Path.home() / ".claude")
    inv.add_argument("--codex-dir", type=Path, default=Path.home() / ".codex")
    inv.add_argument("--prices", type=Path, default=TOOL_DIR / "prices.json")
    inv.add_argument("--out-md", type=Path, help="report path (default: workflow/usage/runs/RUN_ID/report-v2.md)")
    inv.add_argument("--out-csv", type=Path, help="metrics CSV path (default: workflow/usage/runs/RUN_ID/metrics-v2.csv)")
    inv.add_argument("session_ids", metavar="SESSION_ID", nargs="+")
    return parser


def invocations_from_logs(args, prices: dict) -> int:
    """Checks run in order: run ID, session IDs, logs, build, sidecar, cross-check, render, write."""
    try:
        built = build_invocations(args.run_id, args.claude_dir, args.session_ids, prices)
        for warning in built.warnings:
            print(warning, file=sys.stderr)
        records = built.records
        meta = read_metadata(args.meta, [record.invocation_id for record in records])
        sessions = set(args.session_ids)
        report_rows = [
            row for row in collect_rows(args.claude_dir, args.codex_dir, prices) if row.tool == "claude" and row.session_id in sessions
        ]
        unattributed = cross_check([row for record in records for row in record.rows], report_rows, args.session_ids)
        likely = likely_agent_text(unattributed, records)
        rows = metric_rows(records, prices)
        apply_metadata(rows, meta)
        total = total_row(records, rows, prices)
        stray = unattributed_row(args.run_id, unattributed, likely)
        markdown = render_markdown(args.run_id, args.session_ids, rows, total, stray, likely)
        metrics_csv = render_csv([*rows, total, stray])
        run_dir = TOOL_DIR.parents[1] / "usage" / "runs" / args.run_id
        md_path = args.out_md or run_dir / "report-v2.md"
        csv_path = args.out_csv or run_dir / "metrics-v2.csv"
        _write(markdown, md_path, "report", "--out-md")
        _write(metrics_csv, csv_path, "metrics CSV", "--out-csv")
    except TrackerError as exc:
        for line in exc.message.split("\n"):
            print(f"error: {line}", file=sys.stderr)
        return exc.exit_code
    print(f"Wrote invocation report for run {args.run_id} ({len(records)} invocations) to {md_path} and {csv_path}")
    return 0


def _write(text: str, path: Path, kind: str, option: str) -> None:
    try:
        write_report(text, path)
    except OSError as exc:
        raise TrackerError(f'cannot write the {kind} to {option} "{path}": {exc.strerror or exc}') from None


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    prices = load_prices(args.prices if args.prices.is_file() else None)
    if args.command == "invocations-from-logs":
        return invocations_from_logs(args, prices)
    if args.command == "run-report":
        try:
            feature_run_id, invocations = read_manifest(args.manifest)
            rows = collect_rows(args.claude_dir, args.codex_dir, prices)
            report = render_report(feature_run_id, invocations, rows)
        except (AttributionError, ManifestError, OSError, UnicodeError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        output = args.out or args.manifest.parent / "report.md"
        write_report(report, output)
        print(f"Wrote feature-run report for {feature_run_id} ({len(invocations)} invocations) to {output}")
        return 0
    rows = collect_rows(args.claude_dir, args.codex_dir, prices, args.cwd_contains, args.since)
    if args.command == "export":
        write_csv(rows, args.out)
        print(f"Wrote {len(rows)} rows to {args.out}")
        return 0
    summary = summarise(rows, args.branch)
    print(render_table(summary))
    if args.out:
        write_summary_csv(summary, args.out)
        print(f"Wrote summary to {args.out}")
    return 0
