import unittest
from types import SimpleNamespace

from compare import build_row, cell, render_markdown, run_rows, COLUMNS

TOTAL = {
    "requests": 10, "input_tokens": 100, "cache_read_tokens": 1000,
    "cache_write_5m_tokens": 20, "cache_write_1h_tokens": 30,
    "output_tokens": 400, "reasoning_tokens": 50, "cost_usd": 2.0,
}
GRADE = {"grader": {"passed": 16, "total": 18}, "own_tests": {"passed": 9, "total": 9}}


class CompareTest(unittest.TestCase):
    def test_row_combines_usage_grade_and_notes(self):
        row = build_row("A", TOTAL, GRADE, {"revision_rounds": 1})
        self.assertEqual(row["total_tokens"], 100 + 1000 + 50 + 400)
        self.assertEqual(row["cache_write_tokens"], 50)
        self.assertEqual(row["grader_pct"], 88.9)
        self.assertAlmostEqual(row["cost_per_grader_pass_usd"], 2.0 / 16)
        self.assertEqual(row["revision_rounds"], 1)

    def test_missing_grade_or_cost_gives_blanks_not_errors(self):
        row = build_row("B", dict(TOTAL, cost_usd=None), None, {})
        self.assertIsNone(row["grader_pct"])
        self.assertIsNone(row["cost_per_grader_pass_usd"])
        self.assertEqual(cell(row["cost_usd"]), "n/a")

    def test_zero_passes_does_not_divide_by_zero(self):
        row = build_row("A", TOTAL, {"grader": {"passed": 0, "total": 18}}, {})
        self.assertIsNone(row["cost_per_grader_pass_usd"])

    def test_run_rows_include_subagents_logged_on_another_branch(self):
        rows = [
            SimpleNamespace(session_id="s1", branch="exp/stu02-A"),
            SimpleNamespace(session_id="s1", branch="worktree-agent-x"),
            SimpleNamespace(session_id="s2", branch="exp/stu02-B"),
            SimpleNamespace(session_id="s3", branch="master"),
        ]
        picked = run_rows(rows, "exp/stu02-A")
        self.assertEqual([r.branch for r in picked], ["exp/stu02-A", "worktree-agent-x"])

    def test_markdown_has_header_and_one_line_per_run(self):
        text = render_markdown([build_row("A", TOTAL, GRADE, {}), build_row("B", TOTAL, GRADE, {})])
        lines = text.splitlines()
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[0].count("|"), len(COLUMNS) + 1)


if __name__ == "__main__":
    unittest.main()
