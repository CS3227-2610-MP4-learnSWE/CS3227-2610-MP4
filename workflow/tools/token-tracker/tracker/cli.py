"""Command line: `export` writes row-level usage, `report` summarises it."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .export import collect_rows, write_csv
from .pricing import load_prices
from .report import render_table, summarise, write_summary_csv
from .run_report import AttributionError, ManifestError, read_manifest, render_report, write_report

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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    prices = load_prices(args.prices if args.prices.is_file() else None)
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
