import unittest

from helpers_trk03 import PRICES, TrackerCase, assistant, user
from tracker.crosscheck import cross_check
from tracker.errors import TrackerError
from tracker.export import collect_rows
from tracker.model import UsageRow
from tracker.report import summarise


def urow(session="s1", agent="a1", out=5, ts="2026-11-01T00:00:01.000Z"):
    return UsageRow(
        tool="claude", session_id=session, agent_id=agent, agent_type="developer", is_subagent=True, model="claude-sonnet-5-5",
        branch="", cwd="", timestamp=ts, input_tokens=10, cache_read_tokens=0, cache_write_5m_tokens=0, cache_write_1h_tokens=0,
        output_tokens=out, reasoning_tokens=0, cost_usd=0.0001,
    )


class CrossCheckFunctionTest(unittest.TestCase):
    def test_trk03_crosscheck_returns_unattributed_rows(self):  # AC19, AC20
        a, b, extra = urow(out=1), urow(out=2), urow(agent="", out=3)
        self.assertEqual(cross_check([a, b], [b, a], ["s1"]), [])
        self.assertEqual(cross_check([a], [a, extra], ["s1"]), [extra])

    def test_trk03_crosscheck_raises_exit_1_for_missing_report_row(self):  # AC21
        with self.assertRaises(TrackerError) as ctx:
            cross_check([urow(out=1), urow(out=2)], [urow(out=1)], ["s1"])
        self.assertEqual(ctx.exception.exit_code, 1)
        self.assertIn("1 invocation request(s) have no identical row in the report", ctx.exception.message)


class CrossCheckCliTest(TrackerCase):
    def setUp(self):
        super().setUp()
        self.logs.sub("s1", "a1", [user("PROMPT_SENTINEL", 0), assistant("m1", 1, out=10)])

    def stray_copy(self):
        self.logs.stray("s1", [{"agentId": "a1", **assistant("m1", 1, out=99)}])

    def test_trk03_crosscheck_sums_equal_report_total(self):  # AC20
        self.logs.sub("s1", "a2", [user("P", 5), assistant("m2", 6, out=3), assistant("m3", 7, inp=4, cr=9, w1=2)])
        self.logs.main("s2", [user("P", 0), assistant("m4", 1, model="claude-haiku-5-5", inp=100001)])
        result = self.run_cli(["s1", "s2"])
        self.assertEqual(result.code, 0, result.err)
        rows = [r for r in collect_rows(self.logs.claude, self.logs.codex, PRICES) if r.session_id in ("s1", "s2")]
        report = summarise(rows)[-1]
        total, stray = result.kind("run_total")[0], result.kind("unattributed")[0]
        for column, key in (
            ("requests", "requests"), ("input_tokens", "input_tokens"), ("cache_read_tokens", "cache_read_tokens"),
            ("cache_write_5m_tokens", "cache_write_5m_tokens"), ("cache_write_1h_tokens", "cache_write_1h_tokens"),
            ("output_tokens", "output_tokens"), ("reasoning_tokens", "reasoning_tokens"),
        ):
            self.assertEqual(int(total[column]) + int(stray[column]), report[key], column)
        self.assertAlmostEqual(float(total["cost_usd"]), report["cost_usd"], places=6)
        self.assertEqual(stray["requests"], "0")

    def test_trk03_crosscheck_mismatch_exit_1_nothing_written(self):  # AC21
        self.stray_copy()
        result = self.run_cli(["s1"])
        self.assertEqual(result.code, 1)
        self.assertFalse(self.md_path.exists() or self.csv_path.exists())
        self.assertEqual(result.out, "")

    def test_trk03_crosscheck_keeps_existing_output_files(self):  # AC21
        self.stray_copy()
        self.md_path.parent.mkdir(parents=True)
        self.md_path.write_text("OLD MD", encoding="utf-8")
        self.csv_path.write_text("OLD CSV", encoding="utf-8")
        self.assertEqual(self.run_cli(["s1"]).code, 1)
        self.assertEqual((self.md_path.read_text(encoding="utf-8"), self.csv_path.read_text(encoding="utf-8")), ("OLD MD", "OLD CSV"))

    def test_trk03_crosscheck_message_lines_follow_the_contract(self):  # AC21
        self.stray_copy()
        prefix = "error: cross-check failed for session(s) s1: "
        self.assertEqual(
            self.run_cli(["s1"]).err_lines(),
            [
                prefix + "1 invocation request(s) have no identical row in the report (affected sources: s1/a1); "
                "report rows: 1, invocation rows plus unattributed rows: 2",
                prefix + "requests: invocations plus unattributed = 2, report = 1, difference (report minus invocations plus unattributed) = -1",
                prefix + "input_tokens: invocations plus unattributed = 20, report = 10, difference (report minus invocations plus unattributed) = -10",
                prefix + "output_tokens: invocations plus unattributed = 109, report = 99, difference (report minus invocations plus unattributed) = -10",
                prefix + "cost_usd: invocations plus unattributed = 0.001130, report = 0.001010, difference (report minus invocations plus unattributed) = -0.000120",
                prefix + "likely cause: a message ID is logged in more than one file for these sessions (for example a copy of a log "
                "outside the session folder layout) with a larger output_tokens, so the report keeps a different line than the invocation reader",
            ],
        )

    def test_trk03_crosscheck_message_names_sessions_sorted(self):  # AC21
        self.stray_copy()
        self.logs.main("s0", [user("P", 0), assistant("z1", 1)])
        self.assertTrue(self.run_cli(["s1", "s0"]).err_lines()[0].startswith("error: cross-check failed for session(s) s0, s1: "))

    def test_trk03_crosscheck_message_has_no_log_text(self):  # AC21, AC22
        self.stray_copy()
        self.assertNotIn("PROMPT_SENTINEL", self.run_cli(["s1"]).err)


class UnattributedTest(TrackerCase):
    def setUp(self):
        super().setUp()
        self.logs.sub("s1", "a1", [user("P", 0), assistant("m1", 100)])

    def md_line(self, result):
        return next(line for line in result.md.splitlines() if line.startswith("Unattributed usage"))

    def guess(self, result):
        return result.kind("unattributed")[0]["likely_agent_inferred_guess"]

    def test_trk03_unattributed_zero_when_all_claimed(self):  # AC19
        result = self.run_cli(["s1"])
        stray = result.kind("unattributed")[0]
        self.assertEqual((stray["requests"], stray["cost_usd"]), ("0", "0.000000"))

    def test_trk03_unattributed_counts_stray_session_log(self):  # AC19
        self.logs.stray("s1", [assistant("x1", 50, inp=7, out=3)])
        result = self.run_cli(["s1"])
        self.assertEqual(result.code, 0, result.err)
        stray = result.kind("unattributed")[0]
        self.assertEqual((stray["requests"], stray["input_tokens"], stray["output_tokens"], stray["cost_usd"]), ("1", "7", "3", "0.000044"))
        self.assertEqual(
            self.md_line(result),
            "Unattributed usage (rows in the listed sessions that no invocation claims): requests=1, input=7, cache_read=0, "
            "cache_write_5m=0, cache_write_1h=0, output=3, reasoning=0, cost_usd=0.000044; "
            "likely_agent (inferred guess, not measured): RUN-developer-01 (rule: window; requests: 1)",
        )

    def test_trk03_unattributed_unpriced_cost_unavailable(self):  # AC19
        self.logs.stray("s1", [assistant("x1", 50, model="mystery")])
        self.assertEqual(self.run_cli(["s1"]).kind("unattributed")[0]["cost_usd"], "unavailable")

    def test_trk03_unattributed_is_not_an_error_and_totals_reconcile(self):  # AC19, AC20
        self.logs.stray("s1", [assistant("x1", 50, inp=7)])
        result = self.run_cli(["s1"])
        rows = [r for r in collect_rows(self.logs.claude, self.logs.codex, PRICES) if r.session_id == "s1"]
        total, stray = result.kind("run_total")[0], result.kind("unattributed")[0]
        self.assertEqual(int(total["requests"]) + int(stray["requests"]), len(rows))

    def test_trk03_stray_in_another_listed_session_is_attributed_to_that_session(self):  # AC19
        self.logs.main("s2", [user("P", 0), assistant("o1", 10)])
        self.logs.stray("s2", [assistant("x1", 5)], name="other.jsonl")
        self.assertIn("RUN-orchestrator-01 (rule: window; requests: 1)", self.guess(self.run_cli(["s1", "s2"])))

    def test_trk03_likely_agent_window_rule(self):  # AC29
        self.logs.stray("s1", [assistant("x1", 50)])
        self.assertEqual(self.guess(self.run_cli(["s1"])), "RUN-developer-01 (rule: window; requests: 1)")

    def test_trk03_likely_agent_shortest_window_wins(self):  # AC29
        self.logs.main("s1", [user("P", 0), assistant("o1", 1000)])
        self.logs.stray("s1", [assistant("x1", 50)])
        self.assertEqual(self.guess(self.run_cli(["s1"])), "RUN-developer-01 (rule: window; requests: 1)")

    def test_trk03_likely_agent_nearest_when_no_window(self):  # AC29
        self.logs.stray("s1", [assistant("x1", 150)])
        self.assertEqual(self.guess(self.run_cli(["s1"])), "RUN-developer-01 (rule: nearest; requests: 1)")

    def test_trk03_likely_agent_nearest_tie_goes_to_first_in_output_order(self):  # AC29
        self.logs.sub("s1", "a2", [user("P", 200), assistant("m2", 300)])
        self.logs.stray("s1", [assistant("x1", 150)])
        self.assertEqual(self.guess(self.run_cli(["s1"])), "RUN-developer-01 (rule: nearest; requests: 1)")

    def test_trk03_likely_agent_none_when_row_has_no_timestamp(self):  # AC29
        self.logs.stray("s1", [assistant("x1", None)])
        self.assertEqual(self.guess(self.run_cli(["s1"])), "unavailable (rule: none; requests: 1)")

    def test_trk03_likely_agent_none_when_session_invocations_have_no_times(self):  # AC29
        self.logs.sub("s1", "a1", [user("P", None), assistant("m1", None)])
        self.logs.stray("s1", [assistant("x1", 50)])
        self.assertEqual(self.guess(self.run_cli(["s1"])), "unavailable (rule: none; requests: 1)")

    def test_trk03_likely_agent_groups_and_sorts_entries(self):  # AC29
        self.logs.main("s1", [user("P", 0), assistant("o1", 1000)])
        self.logs.stray("s1", [assistant("x1", 50), assistant("x2", 51), assistant("x3", 500), assistant("x4", None)])
        self.assertEqual(
            self.guess(self.run_cli(["s1"])),
            "RUN-developer-01 (rule: window; requests: 2); RUN-orchestrator-01 (rule: window; requests: 1); "
            "unavailable (rule: none; requests: 1)",
        )

    def test_trk03_likely_agent_none_text_without_stray_rows(self):  # AC29
        result = self.run_cli(["s1"])
        self.assertEqual(self.guess(result), "")
        self.assertTrue(self.md_line(result).endswith("likely_agent (inferred guess, not measured): none"))

    def test_trk03_likely_agent_labelled_in_markdown_and_csv_column(self):  # AC29
        self.logs.stray("s1", [assistant("x1", 50)])
        result = self.run_cli(["s1"])
        self.assertIn("inferred guess", self.md_line(result))
        self.assertIn("likely_agent_inferred_guess", result.csv_text.split("\n")[0])
        self.assertEqual({r["likely_agent_inferred_guess"] for r in result.kind("invocation") + result.kind("run_total")}, {""})

    def test_trk03_likely_agent_does_not_change_invocation_rows_or_total(self):  # AC30
        before = self.run_cli(["s1"])
        rows_before, total_before = before.kind("invocation"), before.kind("run_total")
        self.logs.stray("s1", [assistant("x1", 50, inp=7, out=3), assistant("x2", 150)])
        after = self.run_cli(["s1"])
        self.assertEqual(after.kind("invocation"), rows_before)
        self.assertEqual(after.kind("run_total"), total_before)

    def test_trk03_stray_numbers_only_on_unattributed_row(self):  # AC30
        self.logs.stray("s1", [assistant("x1", 50, inp=7, out=3)])
        result = self.run_cli(["s1"])
        self.assertEqual(result.inv()["requests"], "1")
        self.assertEqual(result.kind("run_total")[0]["input_tokens"], result.inv()["input_tokens"])
        self.assertEqual(result.kind("unattributed")[0]["input_tokens"], "7")


if __name__ == "__main__":
    unittest.main()
