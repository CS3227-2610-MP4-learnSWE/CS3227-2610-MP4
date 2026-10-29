import csv
import tempfile
import unittest
from pathlib import Path

from helpers import SECRET, claude_line, codex_meta, codex_session, codex_tokens, codex_turn, write_jsonl
from tracker.export import collect_rows, write_csv
from tracker.model import COLUMNS
from tracker.report import summarise

PRICES = {"models": {"claude-sonnet-5-5": {"input": 1.0, "cache_read": 1.0, "cache_write_5m": 1.0, "cache_write_1h": 1.0, "output": 1.0}}}


class ExportReportTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.claude = self.root / "claude"
        self.codex = self.root / "codex"
        project = self.claude / "projects" / "p"
        write_jsonl(
            project / "s1.jsonl",
            [
                claude_line("a", output=10, branch="exp/a", cwd="C:\\learnSWE", ts="2026-10-29T01:00:00Z"),
                claude_line("b", output=20, branch="exp/b", cwd="C:\\learnSWE", ts="2026-10-29T02:00:00Z"),
                claude_line("c", output=30, branch="exp/a", cwd="C:\\other", ts="2026-10-28T01:00:00Z"),
            ],
        )
        codex_session(
            self.codex / "sessions" / "2026" / "10" / "29" / "rollout-x.jsonl",
            [codex_meta(cwd="C:\\learnSWE", branch="exp/a"), codex_turn("gpt-x"), codex_tokens(100, 0, 5, 0, total=105)],
        )

    def rows(self, **kw):
        return collect_rows(self.claude, self.codex, PRICES, **kw)

    def test_collects_both_tools_sorted_by_time(self):
        rows = self.rows()
        self.assertEqual({r.tool for r in rows}, {"claude", "codex"})
        self.assertEqual([r.timestamp for r in rows], sorted(r.timestamp for r in rows))

    def test_export_is_idempotent_and_has_no_content(self):  # AC7
        out = self.root / "usage.csv"
        write_csv(self.rows(), out)
        first = out.read_bytes()
        write_csv(self.rows(), out)
        self.assertEqual(first, out.read_bytes())
        self.assertNotIn(SECRET.encode(), first)
        with out.open(newline="", encoding="utf-8") as fh:
            self.assertEqual(next(csv.reader(fh)), COLUMNS)

    def test_cwd_filter(self):  # AC9
        rows = self.rows(cwd_contains="learnSWE")
        self.assertEqual(len(rows), 3)
        self.assertTrue(all("learnSWE" in r.cwd for r in rows))

    def test_since_filter(self):
        rows = self.rows(since="2026-10-29")
        self.assertTrue(all(r.timestamp >= "2026-10-29" for r in rows))
        self.assertEqual(len(rows), 3)

    def test_report_filters_by_branch_and_totals(self):  # AC8
        summary = summarise(self.rows(), branch="exp/a")
        total = summary[-1]
        self.assertEqual(total["agent_type"], "TOTAL")
        body = summary[:-1]
        self.assertEqual(sum(g["output_tokens"] for g in body), total["output_tokens"])
        self.assertEqual(total["output_tokens"], 10 + 30 + 5)
        self.assertEqual({(g["agent_type"], g["model"]) for g in body}, {("main", "claude-sonnet-5-5"), ("main", "gpt-x")})

    def test_report_cost_blank_when_any_price_missing(self):  # AC6/AC8
        summary = summarise(self.rows(), branch="exp/a")
        by_model = {g["model"]: g for g in summary[:-1]}
        self.assertIsNotNone(by_model["claude-sonnet-5-5"]["cost_usd"])
        self.assertIsNone(by_model["gpt-x"]["cost_usd"])
        self.assertIsNone(summary[-1]["cost_usd"])


if __name__ == "__main__":
    unittest.main()
