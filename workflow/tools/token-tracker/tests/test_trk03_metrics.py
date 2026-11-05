import unittest

from helpers_trk03 import T, TrackerCase, assistant, result, tu, user

U = "unavailable"


class ModelAndCostTest(TrackerCase):
    def test_trk03_model_match_yes_no_unavailable(self):  # AC9
        row = self.one_sub([assistant("m1", 1)]).inv()
        self.assertEqual((row["requested_model"], row["observed_models"], row["model_match"]), ("claude-sonnet-5-5",) * 2 + ("yes",))
        self.setUp()
        row = self.one_sub([assistant("m1", 1), assistant("m2", 2, requested="claude-opus-5-5")]).inv()
        self.assertEqual(row["model_match"], "no")
        self.assertEqual(row["requested_model"], "claude-opus-5-5; claude-sonnet-5-5")
        self.setUp()
        row = self.one_sub([assistant("m1", 1, requested=None)]).inv()
        self.assertEqual((row["requested_model"], row["model_match"]), (U, U))
        self.assertEqual(row["observed_models"], "claude-sonnet-5-5")

    def test_trk03_observed_models_sorted_joined(self):  # AC9
        row = self.one_sub([assistant("m1", 1, model="claude-sonnet-5-5"), assistant("m2", 2, model="claude-haiku-5-5")]).inv()
        self.assertEqual(row["observed_models"], "claude-haiku-5-5; claude-sonnet-5-5")

    def test_trk03_cost_split_by_type_sums_to_cost(self):  # AC10
        row = self.one_sub([assistant("m1", 1, inp=1000, cr=2000, w5=3000, w1=4000, out=500)]).inv()
        self.assertEqual(
            [row[c] for c in ("cost_input", "cost_cache_read", "cost_cache_write_5m", "cost_cache_write_1h", "cost_output", "cost_usd")],
            ["0.002000", "0.000200", "0.007500", "0.016000", "0.005000", "0.030700"],
        )

    def test_trk03_unpriced_model_cost_columns_unavailable(self):  # AC10
        row = self.one_sub([assistant("m1", 1, model="mystery-model")]).inv()
        for column in ("cost_input", "cost_cache_read", "cost_cache_write_5m", "cost_cache_write_1h", "cost_output", "cost_usd"):
            self.assertEqual(row[column], U, column)

    def test_trk03_haiku_tier_applies_per_request_in_invocation(self):  # AC10
        row = self.one_sub(
            [
                assistant("m1", 1, model="claude-haiku-5-5", inp=100000, out=0),
                assistant("m2", 2, model="claude-haiku-5-5-20261105", inp=100002, out=0),
            ]
        ).inv()
        self.assertEqual((row["cost_input"], row["cost_usd"]), ("0.060001", "0.060001"))

    def test_trk03_cost_unavailable_when_no_requests(self):  # AC10, AC14
        row = self.one_sub([]).inv()
        self.assertEqual((row["requests"], row["cost_usd"], row["observed_models"]), ("0", U, U))


class CacheAndContextTest(TrackerCase):
    def test_trk03_reasoning_share(self):  # AC11
        row = self.one_sub([assistant("m1", 1, thinking=30, out=100), assistant("m2", 2, thinking=10, out=100)]).inv()
        self.assertEqual(row["reasoning_share"], "0.2000")
        self.assertEqual(row["reasoning_tokens"], "40")

    def test_trk03_reasoning_share_unavailable_without_field(self):  # AC11, AC14
        self.assertEqual(self.one_sub([assistant("m1", 1, thinking=None, out=100)]).inv()["reasoning_share"], U)
        self.setUp()
        mixed = self.one_sub([assistant("m1", 1, thinking=30, out=100), assistant("m2", 2, thinking=None, out=900)]).inv()
        self.assertEqual(mixed["reasoning_share"], "0.3000")
        self.setUp()
        self.assertEqual(self.one_sub([assistant("m1", 1, thinking=0, out=0)]).inv()["reasoning_share"], U)

    def test_trk03_cache_hit_ratio(self):  # AC11
        row = self.one_sub([assistant("m1", 1, inp=100, cr=300, w5=100)]).inv()
        self.assertEqual(row["cache_hit_ratio"], "0.6000")
        self.setUp()
        self.assertEqual(self.one_sub([assistant("m1", 1, inp=0, cr=0)]).inv()["cache_hit_ratio"], U)

    def test_trk03_zero_cache_read_after_first(self):  # AC11
        reqs = [assistant(f"m{i}", i + 1, cr=cr) for i, cr in enumerate([0, 0, 5, 0])]
        self.assertEqual(self.one_sub(reqs).inv()["zero_cache_read_after_first"], "2")
        self.setUp()
        self.assertEqual(self.one_sub([assistant("m1", 1, cr=0)]).inv()["zero_cache_read_after_first"], "0")

    def test_trk03_cache_write_after_gap_over_300s(self):  # AC11
        row = self.one_sub([assistant("m1", 10), assistant("m2", 311, w5=10, w1=5)]).inv()
        self.assertEqual((row["cache_writes_after_gap"], row["cache_write_tokens_after_gap"]), ("1", "15"))

    def test_trk03_gap_exactly_300s_not_counted(self):  # AC11
        row = self.one_sub([assistant("m1", 10), assistant("m2", 310, w5=10)]).inv()
        self.assertEqual((row["cache_writes_after_gap"], row["cache_write_tokens_after_gap"]), ("0", "0"))
        self.setUp()
        row = self.one_sub([assistant("m1", 10), assistant("m2", 400, w5=0)]).inv()  # long gap but no write
        self.assertEqual(row["cache_writes_after_gap"], "0")

    def test_trk03_gap_single_request_gives_zero(self):  # AC11
        row = self.one_sub([assistant("m1", 10, w5=10)]).inv()
        self.assertEqual((row["cache_writes_after_gap"], row["cache_write_tokens_after_gap"]), ("0", "0"))

    def test_trk03_gap_skipped_when_timestamp_missing(self):  # AC11, AC14
        row = self.one_sub([assistant("m1", 10), assistant("m2", None, w5=10)]).inv()
        self.assertEqual((row["cache_writes_after_gap"], row["cache_write_tokens_after_gap"]), (U, U))
        self.setUp()
        row = self.one_sub([assistant("m1", 10), assistant("m2", 311, w5=5), assistant("m3", None, w5=7)]).inv()
        self.assertEqual((row["cache_writes_after_gap"], row["cache_write_tokens_after_gap"]), ("1", "5"))

    def test_trk03_context_first_max_mean(self):  # AC11
        row = self.one_sub([assistant("m1", 1, inp=10, cr=90), assistant("m2", 2, inp=50, w5=150)]).inv()
        self.assertEqual((row["context_first"], row["context_max"], row["context_mean"]), ("100", "200", "150.0"))
        self.setUp()
        row = self.one_sub([]).inv()
        self.assertEqual((row["context_first"], row["context_max"], row["context_mean"]), (U, U, U))


class ToolsAndFilesTest(TrackerCase):
    def test_trk03_tool_calls_counted_once_per_id_across_duplicate_lines(self):  # AC12
        row = self.one_sub(
            [
                assistant("m1", 1, [tu("t1", "Bash", command="x")]),
                assistant("m1", 1.1, [tu("t1", "Bash", command="x"), {"type": "tool_use", "name": "Bash", "input": {}}], out=9),
                assistant("m2", 2, [tu("t2", "Read", file_path="a.py")]),
            ]
        ).inv()
        self.assertEqual((row["requests"], row["tool_calls"]), ("2", "2"))

    def test_trk03_tool_calls_by_name_sorted(self):  # AC12
        row = self.one_sub(
            [assistant("m1", 1, [tu("t1", "Write", file_path="a"), tu("t2", "Bash", command="x"), tu("t3", "Bash", command="y")])]
        ).inv()
        self.assertEqual(row["tool_calls_by_name"], "Bash=2; Write=1")
        self.setUp()
        row = self.one_sub([assistant("m1", 1)]).inv()
        self.assertEqual((row["tool_calls"], row["tool_calls_by_name"], row["failed_tool_calls"]), ("0", "none", "0"))

    def test_trk03_failed_tool_calls_is_error(self):  # AC12
        row = self.one_sub(
            [
                assistant("m1", 1, [tu("t1", "Bash", command="x"), tu("t2", "Bash", command="y"), tu("t3", "Bash", command="z")]),
                result("t1", 2, is_error=True),
                result("t2", 3),
            ]
        ).inv()
        self.assertEqual((row["tool_calls"], row["failed_tool_calls"]), ("3", "1"))

    def test_trk03_file_reads_total_distinct_repeated(self):  # AC12
        row = self.one_sub(
            [
                assistant(
                    "m1",
                    1,
                    [
                        tu("t1", "Read", file_path="C:\\Repo\\a.py"),
                        tu("t2", "Read", file_path="c:/Repo/a.py"),
                        tu("t3", "Read", file_path="C:/Repo/b.py", offset=5, limit=10),
                        tu("t4", "Read", file_path="./x/../c.py"),
                        tu("t5", "Read", file_path=""),
                    ],
                )
            ]
        ).inv()
        self.assertEqual((row["files_read"], row["files_distinct"], row["files_repeated"]), ("4", "3", "1"))
        self.assertEqual(row["repeated_paths"], "c:/Repo/a.py")

    def test_trk03_read_path_normalisation(self):  # AC12
        row = self.one_sub(
            [
                assistant(
                    "m1",
                    1,
                    [
                        tu("t1", "Read", file_path="  D:\\p\\q\\..\\f.txt  "),
                        tu("t2", "Read", file_path="d:/p/f.txt"),
                        tu("t3", "Read", file_path="/usr/./lib/x"),
                        tu("t4", "Read", file_path="/usr/lib/x"),
                    ],
                )
            ]
        ).inv()
        self.assertEqual((row["files_read"], row["files_distinct"]), ("4", "2"))
        self.assertEqual(row["repeated_paths"], "/usr/lib/x; d:/p/f.txt")

    def test_trk03_only_read_tool_counts_as_file_read(self):  # AC12
        row = self.one_sub(
            [assistant("m1", 1, [tu("t1", "Grep", pattern="x", path="C:/Repo"), tu("t2", "Glob", pattern="*.py"), tu("t3", "Write", file_path="C:/Repo/w.py")])]
        ).inv()
        self.assertEqual((row["files_read"], row["files_distinct"], row["files_repeated"], row["repeated_paths"]), ("0", "0", "0", ""))


class TimeTest(TrackerCase):
    def test_trk03_elapsed_and_active(self):  # AC13
        row = self.one_sub([assistant("m1", 10, [tu("t1", "Bash", command="x")]), result("t1", 15), assistant("m2", 20)]).inv()
        self.assertEqual((row["started_at"], row["finished_at"]), (T(0), T(20)))
        self.assertEqual((row["elapsed_s"], row["active_s"]), ("20.0", "10.0"))

    def test_trk03_active_single_request_is_zero(self):  # AC13
        self.assertEqual(self.one_sub([assistant("m1", 10)]).inv()["active_s"], "0.0")

    def test_trk03_tool_time_partial_reports_calls_timed(self):  # AC13
        row = self.one_sub(
            [assistant("m1", 10, [tu("t1", "Bash", command="x")]), result("t1", 13), assistant("m2", 20, [tu("t2", "Bash", command="y")]), result("t2", None)]
        ).inv()
        self.assertEqual((row["tool_calls"], row["tool_calls_timed"], row["tool_time_s"]), ("2", "1", "3.0"))

    def test_trk03_tool_time_unavailable_when_no_pair_timed(self):  # AC13, AC14
        row = self.one_sub([assistant("m1", 10, [tu("t1", "Bash", command="x")]), result("t1", None)]).inv()
        self.assertEqual((row["tool_calls"], row["tool_calls_timed"], row["tool_time_s"]), ("1", "0", U))
        self.setUp()
        row = self.one_sub([assistant("m1", 10, [tu("t1", "Bash", command="x")]), result("t1", 5)]).inv()  # result before use
        self.assertEqual((row["tool_calls_timed"], row["tool_time_s"]), ("0", U))

    def test_trk03_tool_time_zero_without_calls(self):  # AC13
        row = self.one_sub([assistant("m1", 10)]).inv()
        self.assertEqual((row["tool_time_s"], row["tool_calls_timed"]), ("0.0", "0"))

    def test_trk03_tool_time_sums_overlapping_calls(self):  # AC13
        row = self.one_sub(
            [assistant("m1", 10, [tu("t1", "Bash", command="x"), tu("t2", "Bash", command="y")]), result("t1", 14), result("t2", 16)]
        ).inv()
        self.assertEqual((row["tool_time_s"], row["tool_calls_timed"]), ("10.0", "2"))

    def test_trk03_wait_before_start_latest_earlier_finish(self):  # AC13
        self.logs.sub("s1", "a1", [user("P", 0), assistant("m1", 100)])
        self.logs.sub("s1", "a2", [user("P", 130), assistant("m2", 150)])
        self.logs.sub("s1", "a3", [user("P", 200), assistant("m3", 210)])
        rows = {r["agent_id"]: r for r in self.run_cli(["s1"]).kind("invocation")}
        self.assertEqual(rows["a2"]["wait_before_start_s"], "30.0")
        self.assertEqual(rows["a3"]["wait_before_start_s"], "50.0")

    def test_trk03_wait_unavailable_when_none_finished_before(self):  # AC13
        self.logs.sub("s1", "a1", [user("P", 0), assistant("m1", 100)])
        self.logs.sub("s1", "a2", [user("P", 50), assistant("m2", 150)])
        rows = {r["agent_id"]: r for r in self.run_cli(["s1"]).kind("invocation")}
        self.assertEqual((rows["a1"]["wait_before_start_s"], rows["a2"]["wait_before_start_s"]), (U, U))

    def test_trk03_human_messages_exclude_prompt_and_meta(self):  # AC13
        row = self.one_sub(
            [user("extra one", 1), user("meta", 2, meta=True), assistant("m1", 3), user("extra two", 4), result("x", 5)]
        ).inv()
        self.assertEqual(row["human_messages"], "2")

    def test_trk03_human_messages_orchestrator_excludes_first_only(self):  # AC13
        self.logs.main("s1", [user("first", 0), assistant("m1", 1), user("second", 2), user("third", 3), user("meta", 4, meta=True)])
        self.assertEqual(self.run_cli(["s1"]).inv()["human_messages"], "2")

    def test_trk03_missing_fields_give_unavailable_not_zero(self):  # AC14
        row = self.one_sub(
            [assistant("m1", None, [tu("t1", "Bash", command="x")]), result("t1", None)], prompt_t=None
        ).inv()
        for column in ("started_at", "finished_at", "elapsed_s", "active_s", "tool_time_s", "wait_before_start_s"):
            self.assertEqual(row[column], U, column)
        self.assertEqual(row["requests"], "1")


if __name__ == "__main__":
    unittest.main()
