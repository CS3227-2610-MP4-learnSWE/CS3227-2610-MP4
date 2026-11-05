import shutil
import unittest
import uuid
from pathlib import Path

from helpers_trk03 import T, TrackerCase, assistant, tu, user
from tracker.invocation_meta import read_metadata

CSV_COLUMNS = (
    "record, run_id, invocation_id, role, role_label, session_id, agent_id, prompt_number, launched_by, requested_agent_type, "
    "requested_model, observed_models, model_match, started_at, finished_at, elapsed_s, active_s, tool_time_s, tool_calls_timed, "
    "wait_before_start_s, requests, input_tokens, cache_read_tokens, cache_write_5m_tokens, cache_write_1h_tokens, output_tokens, "
    "reasoning_tokens, reasoning_share, cache_hit_ratio, zero_cache_read_after_first, cache_writes_after_gap, "
    "cache_write_tokens_after_gap, context_first, context_max, context_mean, cost_usd, cost_input, cost_cache_read, "
    "cost_cache_write_5m, cost_cache_write_1h, cost_output, tool_calls, failed_tool_calls, tool_calls_by_name, files_read, "
    "files_distinct, files_repeated, repeated_paths, human_messages, arm, phase, revision_round, trigger, start_commit, "
    "end_commit, agent_definition_hash, likely_agent_inferred_guess"
).split(", ")

TABLE_A = (
    "| Invocation ID | Role | Role label | Session ID | Agent ID | Prompt | Launched by | Requested agent type | Requested model | "
    "Observed model(s) | Model match | Started | Finished | Elapsed (s) | Requests | Input | Cache read | Cache write (5m) | "
    "Cache write (1h) | Output | Reasoning | Cost (USD) |"
)
HEADERS = {
    "B": "| Invocation ID | Reasoning share | Cache hit ratio | Zero cache read after first | Cache writes after gap | Cache write tokens after gap | First context | Max context | Mean context |",
    "C": "| Invocation ID | Tool calls | Failed tool calls | Tool calls by name | Files read | Distinct files | Repeated reads | Human messages | Active (s) | Tool time (s) | Tool calls timed | Wait before start (s) |",
    "D": "| Invocation ID | Input | Cache read | Cache write (5m) | Cache write (1h) | Output | Total |",
    "E": "| Invocation ID | Arm | Phase | Revision round | Trigger | Start commit | End commit | Agent definition hash |",
}
META_HEADER = "invocation_id, role_label, arm, phase, revision_round, trigger, start_commit, end_commit, agent_definition_hash"
ZERO_LINE = (
    "Unattributed usage (rows in the listed sessions that no invocation claims): requests=0, input=0, cache_read=0, "
    "cache_write_5m=0, cache_write_1h=0, output=0, reasoning=0, cost_usd=0.000000; "
    "likely_agent (inferred guess, not measured): none"
)


class SidecarTest(TrackerCase):
    def setUp(self):
        super().setUp()
        self.logs.sub("s1", "a1", [user("P", 0), assistant("m1", 1)])

    def test_trk03_sidecar_columns_in_csv_and_markdown(self):  # AC15
        meta = self.write_meta(["RUN-developer-01, Lbl ,armA, phaseB ,2,revision,abc123,def456,hash9"])
        result = self.run_cli(["s1"], meta=meta)
        row = result.inv()
        self.assertEqual(
            [row[c] for c in ("role_label", "arm", "phase", "revision_round", "trigger", "start_commit", "end_commit", "agent_definition_hash")],
            ["Lbl", "armA", "phaseB", "2", "revision", "abc123", "def456", "hash9"],
        )
        self.assertIn("| RUN-developer-01 | armA | phaseB | 2 | revision | abc123 | def456 | hash9 |", result.md)

    def test_trk03_no_sidecar_columns_blank(self):  # AC15
        row = self.run_cli(["s1"]).inv()
        for column in ("role_label", "arm", "phase", "revision_round", "trigger", "start_commit", "end_commit", "agent_definition_hash"):
            self.assertEqual(row[column], "", column)

    def test_trk03_sidecar_partial_rows_and_bom(self):  # AC15
        self.logs.sub("s1", "a2", [user("P", 5), assistant("m2", 6)])
        path = self.root / "meta.csv"
        header = "invocation_id,role_label,arm,phase,revision_round,trigger,start_commit,end_commit,agent_definition_hash"
        path.write_text(header + "\nRUN-developer-02,,,build,,first,,,\n", encoding="utf-8-sig")
        result = self.run_cli(["s1"], meta=path)
        self.assertEqual(result.code, 0, result.err)
        self.assertEqual(result.inv("RUN-developer-01")["phase"], "")
        self.assertEqual((result.inv("RUN-developer-02")["phase"], result.inv("RUN-developer-02")["trigger"]), ("build", "first"))

    def test_trk03_sidecar_bad_files_are_rejected_with_exact_text(self):  # AC16
        path = self.root / "meta.csv"
        cases = {
            "unknown": (["RUN-nope-01,,,,,,,,"], None, 'line 2: invocation ID "RUN-nope-01" is not in this run; the run\'s IDs are: RUN-developer-01'),
            "duplicate": (["RUN-developer-01,,,,,,,,", "RUN-developer-01,,,,,,,,"], None, 'line 3: invocation ID "RUN-developer-01" already appears on line 2'),
            "header": ([], "a,b", f'line 1: header is "a, b" but must be exactly: {META_HEADER}'),
            "trigger": (["RUN-developer-01,,,,,maybe,,,"], None, 'line 2: trigger "maybe" is not allowed; use one of: first, retry, revision, resume'),
            "round_negative": (["RUN-developer-01,,,,-1,,,,"], None, 'line 2: revision_round "-1" is not a non-negative integer'),
            "round_text": (["RUN-developer-01,,,,x,,,,"], None, 'line 2: revision_round "x" is not a non-negative integer'),
            "round_float": (["RUN-developer-01,,,,1.5,,,,"], None, 'line 2: revision_round "1.5" is not a non-negative integer'),
            "fields": (["RUN-developer-01,a,b"], None, "line 2: expected 9 fields but found 3"),
        }
        for name, (rows, header, expected) in cases.items():
            meta = self.write_meta(rows, header=header)
            result = self.run_cli(["s1"], meta=meta)
            self.assertEqual(result.code, 2, name)
            self.assertEqual(result.err_lines(), [f'error: --meta file "{meta}" {expected}'], name)
            self.assertFalse(self.md_path.exists() or self.csv_path.exists(), name)

    def test_trk03_sidecar_unreadable_error(self):  # AC16
        missing = self.root / "missing.csv"
        result = self.run_cli(["s1"], meta=missing)
        self.assertEqual(result.code, 2)
        self.assertTrue(result.err_lines()[0].startswith(f'error: --meta file "{missing}" cannot be read: '))
        bad = self.root / "bad.csv"
        bad.write_bytes(b"invocation_id\n\xff\xfe\x00bad\n")
        result = self.run_cli(["s1"], meta=bad)
        self.assertEqual(result.err_lines(), [f'error: --meta file "{bad}" cannot be read: not valid UTF-8 text'])

    def test_trk03_read_metadata_without_file_is_empty(self):  # AC15
        self.assertEqual(read_metadata(None, ["RUN-developer-01"]), {})


class LayoutTest(TrackerCase):
    def setUp(self):
        super().setUp()
        self.logs.sub("s1", "a1", [user("P", 0), assistant("m1", 100, [tu("t1", "Read", file_path="C:/r/a.py")], inp=5)])
        self.logs.sub("s1", "a2", [user("P", 130), assistant("m2", 150, [tu("t2", "Read", file_path="C:/r/a.py")], inp=7)], agent_type="verifier")

    def test_trk03_markdown_layout_and_headers(self):  # AC17
        result = self.run_cli(["s1"])
        lines = result.md.split("\n")
        self.assertEqual(lines[0], "# Invocation report: RUN")
        self.assertEqual(lines[2], "Format: `invocation-v2`")
        self.assertEqual(lines[4], "Sessions: s1")
        self.assertIn("tracker list-price estimates, not billed", result.md)
        headings = [line for line in lines if line.startswith("## ")]
        self.assertEqual(headings, ["## Invocations", "## Cache and context", "## Tools, files and time", "## Cost by token type (USD)", "## Metadata"])
        self.assertIn(TABLE_A, lines)
        self.assertIn("| " + " | ".join(["---"] * 22) + " |", lines)
        for key, header in HEADERS.items():
            self.assertIn(header, lines, key)
        self.assertIn(ZERO_LINE, lines)
        self.assertTrue(result.md.endswith("|\n") or result.md.endswith("\n"))
        self.assertFalse(result.md.endswith("\n\n"))
        self.assertNotIn("\r", result.md)
        self.assertEqual(sum(1 for line in lines if line.startswith("| TOTAL |")), 4)  # tables A to D, not E

    def test_trk03_csv_columns_and_row_kinds(self):  # AC17
        result = self.run_cli(["s1"])
        self.assertEqual(len(CSV_COLUMNS), 57)
        self.assertEqual(result.csv_text.split("\n")[0], ",".join(CSV_COLUMNS))
        self.assertEqual([r["record"] for r in result.rows()], ["invocation", "invocation", "run_total", "unattributed"])
        total, stray = result.kind("run_total")[0], result.kind("unattributed")[0]
        self.assertEqual((total["role"], total["invocation_id"], stray["role"], stray["invocation_id"]), ("TOTAL", "", "UNATTRIBUTED", ""))
        self.assertEqual((stray["requests"], stray["input_tokens"]), ("0", "0"))
        self.assertEqual(stray["started_at"], "")
        self.assertEqual(stray["likely_agent_inferred_guess"], "")
        self.assertTrue(result.csv_text.endswith("\n"))
        self.assertNotIn("\r", result.csv_text)
        self.assertEqual({r["run_id"] for r in result.rows()}, {"RUN"})

    def test_trk03_run_total_elapsed_latest_finish_minus_earliest_start(self):  # AC17
        total = self.run_cli(["s1"]).kind("run_total")[0]
        self.assertEqual((total["started_at"], total["finished_at"], total["elapsed_s"]), (T(0), T(150), "150.0"))

    def test_trk03_total_row_sums_and_merges(self):  # AC17
        total = self.run_cli(["s1"]).kind("run_total")[0]
        self.assertEqual((total["requests"], total["input_tokens"]), ("2", "12"))
        self.assertEqual((total["files_read"], total["files_distinct"], total["files_repeated"]), ("2", "1", "1"))
        self.assertEqual(total["repeated_paths"], "")
        self.assertEqual(total["model_match"], "yes")
        self.assertEqual(total["tool_calls_by_name"], "Read=2")
        for column in ("role_label", "session_id", "agent_id", "launched_by", "wait_before_start_s", "active_s", "arm"):
            self.assertEqual(total[column], "", column)

    def test_trk03_total_cost_unavailable_if_any_invocation_unavailable(self):  # AC17
        self.logs.sub("s1", "a3", [user("P", 160), assistant("m3", 170, model="mystery")])
        total = self.run_cli(["s1"]).kind("run_total")[0]
        self.assertEqual((total["cost_usd"], total["cost_input"]), ("unavailable", "unavailable"))

    def test_trk03_rerun_byte_identical_markdown_and_csv(self):  # AC18
        first = self.run_cli(["s1"])
        md, csv_bytes = self.md_path.read_bytes(), self.csv_path.read_bytes()
        self.run_cli(["s1"])
        self.assertEqual((self.md_path.read_bytes(), self.csv_path.read_bytes()), (md, csv_bytes))
        self.assertEqual(first.code, 0)

    def test_trk03_default_output_paths(self):  # AC18
        run_id = f"trk03-default-{uuid.uuid4().hex[:8]}"
        folder = Path(__file__).resolve().parents[3] / "usage" / "runs" / run_id
        self.addCleanup(shutil.rmtree, folder, True)
        result = self.run_cli(["s1"], run_id=run_id, default_paths=True)
        self.assertEqual(result.code, 0, result.err)
        self.assertTrue((folder / "report-v2.md").is_file())
        self.assertTrue((folder / "metrics-v2.csv").is_file())
        self.assertIn(f"to {folder / 'report-v2.md'} and {folder / 'metrics-v2.csv'}", result.out)

    def test_trk03_out_md_out_csv_options(self):  # AC18
        self.md_path = self.root / "deep" / "er" / "a.md"
        self.csv_path = self.root / "deep" / "er" / "b.csv"
        self.assertEqual(self.run_cli(["s1"]).code, 0)
        self.assertTrue(self.md_path.is_file() and self.csv_path.is_file())

    def test_trk03_float_formats_and_unavailable_token(self):  # AC18
        row = self.run_cli(["s1"]).inv("RUN-developer-01")
        self.assertRegex(row["cost_usd"], r"^\d+\.\d{6}$")
        self.assertRegex(row["elapsed_s"], r"^\d+\.\d$")
        self.assertRegex(row["cache_hit_ratio"], r"^\d\.\d{4}$")
        self.assertEqual(row["tool_calls"], "1")
        self.assertEqual(row["wait_before_start_s"], "unavailable")
        self.assertEqual(row["reasoning_share"], "0.0000")

    def test_trk03_markdown_escapes_table_delimiters(self):  # AC18
        meta = self.write_meta(["RUN-developer-01,a|b,x,y,,,,,"])
        result = self.run_cli(["s1"], meta=meta)
        self.assertIn("a\\|b", result.md)
        self.assertEqual(result.inv("RUN-developer-01")["role_label"], "a|b")


if __name__ == "__main__":
    unittest.main()
