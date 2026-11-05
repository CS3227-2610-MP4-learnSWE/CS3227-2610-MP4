import unittest

from helpers_trk03 import TrackerCase, assistant, handback_pair, tu, user

SPEC_CALL = "toolu_spec1"


def main_with_agent_call(logs, session="s1", subagent_type="spec-writer", tool_id=SPEC_CALL, **extra_input):
    logs.main(
        session,
        [user("ORCH PROMPT", 0), assistant("om1", 1, [tu(tool_id, "Agent", subagent_type=subagent_type, **extra_input)])],
    )


class CuttingTest(TrackerCase):
    def test_trk03_one_invocation_per_subagent_and_orchestrator_row(self):  # AC4
        main_with_agent_call(self.logs)
        self.logs.sub("s1", "a1", [user("P", 2), assistant("m1", 3)], agent_type="developer", tool_use_id=SPEC_CALL)
        result = self.run_cli(["s1"])
        self.assertEqual(result.code, 0, result.err)
        ids = [r["invocation_id"] for r in result.kind("invocation")]
        self.assertEqual(ids, ["RUN-orchestrator-01", "RUN-developer-01"])
        self.assertEqual(
            result.out.strip(), f"Wrote invocation report for run RUN (2 invocations) to {self.md_path} and {self.csv_path}"
        )

    def test_trk03_ids_numbered_per_role_by_start_time(self):  # AC4
        self.logs.sub("s1", "a1", [user("P", 50), assistant("m1", 51)])
        self.logs.sub("s1", "a2", [user("P", 10), assistant("m2", 11)])
        self.logs.sub("s1", "a3", [user("P", 30), assistant("m3", 31)], agent_type="verifier")
        result = self.run_cli(["s1"])
        by_agent = {r["agent_id"]: r["invocation_id"] for r in result.kind("invocation")}
        self.assertEqual(by_agent, {"a2": "RUN-developer-01", "a1": "RUN-developer-02", "a3": "RUN-verifier-01"})
        self.assertEqual([r["agent_id"] for r in result.kind("invocation")], ["a2", "a3", "a1"])

    def test_trk03_id_order_ties_broken_by_session_agent_prompt(self):  # AC4
        for session, agent in (("s2", "a1"), ("s1", "a2"), ("s1", "a1")):
            self.logs.sub(session, agent, [user("P", 5), assistant(f"m-{session}-{agent}", 6)])
        result = self.run_cli(["s2", "s1"])
        order = [(r["session_id"], r["agent_id"]) for r in result.kind("invocation")]
        self.assertEqual(order, [("s1", "a1"), ("s1", "a2"), ("s2", "a1")])
        self.assertEqual(result.inv("RUN-developer-01")["session_id"], "s1")

    def test_trk03_multiple_sessions_one_run(self):  # AC4, AC8
        self.logs.main("s1", [user("P", 0), assistant("m1", 1)])
        self.logs.main("s2", [user("P", 5), assistant("m2", 6)])
        result = self.run_cli(["s1", "s2"])
        self.assertEqual(result.code, 0, result.err)
        self.assertEqual([r["invocation_id"] for r in result.kind("invocation")], ["RUN-orchestrator-01", "RUN-orchestrator-02"])
        self.assertIn("Sessions: s1, s2", result.md)

    def test_trk03_session_with_only_subagent_files_has_no_orchestrator_row(self):  # AC4
        self.logs.sub("s1", "a1", [user("P", 0), assistant("m1", 1)])
        result = self.run_cli(["s1"])
        self.assertEqual([r["role"] for r in result.kind("invocation")], ["developer"])

    def test_trk03_resumed_agent_splits_per_handback_prompt(self):  # AC5
        lines = [user("FIRST", 0), assistant("m1", 1)]
        lines += handback_pair("h1", "toolu_h1", 2)
        lines += [user("SECOND", 10, meta=True, prompt_id="p2"), assistant("m2", 11)]
        lines += handback_pair("h2", "toolu_h2", 12)
        self.logs.sub("s1", "a1", lines)
        result = self.run_cli(["s1"])
        rows = result.kind("invocation")
        self.assertEqual([r["invocation_id"] for r in rows], ["RUN-developer-01", "RUN-developer-02"])
        self.assertEqual([r["prompt_number"] for r in rows], ["1", "2"])
        self.assertEqual([r["requests"] for r in rows], ["2", "2"])
        self.assertEqual(rows[1]["started_at"], "2026-11-01T00:00:10.000Z")

    def test_trk03_meta_lines_and_prompt_id_do_not_split(self):  # AC5
        lines = [
            user("P", 0, prompt_id="p1"),
            user("injected", 0.1, meta=True, prompt_id="p1"),
            assistant("m1", 1),
            user("later meta", 2, meta=True, prompt_id="p2"),
            assistant("m2", 3),
        ]
        self.logs.sub("s1", "a1", lines)
        result = self.run_cli(["s1"])
        self.assertEqual(len(result.kind("invocation")), 1)
        self.assertEqual(result.inv()["requests"], "2")

    def test_trk03_file_without_nonmeta_prompt_is_one_invocation(self):  # AC5
        self.logs.sub("s1", "a1", [user("only meta", 0, meta=True), assistant("m1", 1), assistant("m2", 2)])
        result = self.run_cli(["s1"])
        self.assertEqual(len(result.kind("invocation")), 1)
        self.assertEqual(result.inv()["requests"], "2")

    def test_trk03_role_from_meta_agent_type(self):  # AC6
        self.logs.sub("s1", "a1", [user("P", 0), assistant("m1", 1)], agent_type="test-designer")
        result = self.run_cli(["s1"])
        self.assertEqual(result.inv()["role"], "test-designer")
        self.assertEqual(result.inv()["invocation_id"], "RUN-test-designer-01")

    def test_trk03_missing_meta_role_unknown_with_warning_exit_0(self):  # AC6, AC28
        self.logs.sub("s1", "a1", [user("P", 0), assistant("m1", 1)], meta=False)
        result = self.run_cli(["s1"])
        self.assertEqual(result.code, 0)
        self.assertEqual(result.inv()["role"], "unknown")
        self.assertEqual(result.inv()["invocation_id"], "RUN-unknown-01")
        self.assertEqual(
            result.err_lines(),
            [
                "warning: agent a1 in session s1: no usable meta.json (file missing, unreadable or without a text agentType); "
                "role set to unknown"
            ],
        )

    def test_trk03_bad_meta_agent_type_is_unknown(self):  # AC6
        self.logs.sub("s1", "a1", [user("P", 0), assistant("m1", 1)], agent_type=None)
        result = self.run_cli(["s1"])
        self.assertEqual(result.inv()["role"], "unknown")
        self.assertEqual(len(result.err_lines()), 1)

    def test_trk03_role_characters_sanitised(self):  # AC6
        self.logs.sub("s1", "a1", [user("P", 0), assistant("m1", 1)], agent_type="my role/x")
        result = self.run_cli(["s1"])
        self.assertEqual(result.inv()["invocation_id"], "RUN-my_role_x-01")

    def test_trk03_launched_by_matches_agent_tool_use_id(self):  # AC7
        main_with_agent_call(self.logs)
        self.logs.sub("s1", "a1", [user("P", 2), assistant("m1", 3)], tool_use_id=SPEC_CALL)
        result = self.run_cli(["s1"])
        self.assertEqual(result.inv("RUN-developer-01")["launched_by"], "RUN-orchestrator-01")

    def test_trk03_launched_by_unavailable_without_match(self):  # AC7
        main_with_agent_call(self.logs)
        self.logs.sub("s1", "a1", [user("P", 2), assistant("m1", 3)], tool_use_id="toolu_other")
        self.logs.sub("s1", "a2", [user("P", 4), assistant("m2", 5)], tool_use_id="")
        self.logs.sub("s1", "a3", [user("P", 6), assistant("m3", 7)], meta=False)
        rows = self.run_cli(["s1"]).kind("invocation")
        self.assertEqual({r["launched_by"] for r in rows if r["role"] != "orchestrator"}, {"unavailable"})

    def test_trk03_launched_by_unavailable_when_session_has_no_main_file(self):  # AC7
        self.logs.sub("s1", "a1", [user("P", 2), assistant("m1", 3)], tool_use_id=SPEC_CALL)
        self.assertEqual(self.run_cli(["s1"]).inv()["launched_by"], "unavailable")


class RoleObservabilityTest(TrackerCase):  # AC27
    def test_trk03_requested_agent_type_from_agent_call(self):
        main_with_agent_call(self.logs, subagent_type="spec-writer", description="DESC", prompt="PROMPT TEXT")
        self.logs.sub("s1", "a1", [user("P", 2), assistant("m1", 3)], agent_type="general-purpose", tool_use_id=SPEC_CALL)
        row = self.run_cli(["s1"]).inv("RUN-general-purpose-01")
        self.assertEqual(row["role"], "general-purpose")
        self.assertEqual(row["requested_agent_type"], "spec-writer")

    def test_trk03_requested_agent_type_unavailable_without_match(self):
        main_with_agent_call(self.logs)
        self.logs.sub("s1", "a1", [user("P", 2), assistant("m1", 3)], tool_use_id="toolu_nomatch")
        self.assertEqual(self.run_cli(["s1"]).inv("RUN-developer-01")["requested_agent_type"], "unavailable")

    def test_trk03_requested_agent_type_rejects_long_or_odd_text(self):
        for bad in ("has spaces", "x" * 65, "", "semi;colon"):
            self.setUp()
            main_with_agent_call(self.logs, subagent_type=bad)
            self.logs.sub("s1", "a1", [user("P", 2), assistant("m1", 3)], tool_use_id=SPEC_CALL)
            result = self.run_cli(["s1"])
            self.assertEqual(result.inv("RUN-developer-01")["requested_agent_type"], "unavailable", bad)
            if bad:
                self.assertNotIn(bad, result.csv_text + result.md)
        self.setUp()
        main_with_agent_call(self.logs, subagent_type="a.b_c:d-" + "y" * 56)  # exactly 64 characters
        self.logs.sub("s1", "a1", [user("P", 2), assistant("m1", 3)], tool_use_id=SPEC_CALL)
        self.assertEqual(self.run_cli(["s1"]).inv("RUN-developer-01")["requested_agent_type"], "a.b_c:d-" + "y" * 56)

    def test_trk03_orchestrator_row_blank_agent_type_fields(self):
        main_with_agent_call(self.logs)
        row = self.run_cli(["s1"]).inv("RUN-orchestrator-01")
        for column in ("agent_id", "prompt_number", "launched_by", "requested_agent_type", "role_label"):
            self.assertEqual(row[column], "", column)

    def test_trk03_role_label_from_sidecar_shown_next_to_role(self):
        self.logs.sub("s1", "a1", [user("P", 0), assistant("m1", 1)], agent_type="general-purpose")
        meta = self.write_meta(["RUN-general-purpose-01,Spec author,,,,,,,"])
        result = self.run_cli(["s1"], meta=meta)
        self.assertEqual(result.inv()["role_label"], "Spec author")
        header = next(line for line in result.md.splitlines() if line.startswith("| Invocation ID | Role | Role label |"))
        self.assertIn("| Requested agent type |", header)
        self.assertIn("| RUN-general-purpose-01 | general-purpose | Spec author |", result.md)

    def test_trk03_role_label_does_not_change_invocation_id(self):
        self.logs.sub("s1", "a1", [user("P", 0), assistant("m1", 1)])
        plain = self.run_cli(["s1"]).inv()["invocation_id"]
        labelled = self.run_cli(["s1"], meta=self.write_meta([f"{plain},Something else,,,,,,,"])).inv()
        self.assertEqual(labelled["invocation_id"], plain)
        self.assertEqual(labelled["role"], "developer")

    def test_trk03_generic_role_identified_by_label_and_requested_type(self):
        main_with_agent_call(self.logs, subagent_type="verifier")
        self.logs.sub("s1", "a1", [user("P", 2), assistant("m1", 3)], agent_type="general-purpose", tool_use_id=SPEC_CALL)
        meta = self.write_meta(["RUN-general-purpose-01,Final check,,,,,,,"])
        row = self.run_cli(["s1"], meta=meta).inv("RUN-general-purpose-01")
        self.assertEqual((row["role"], row["requested_agent_type"], row["role_label"]), ("general-purpose", "verifier", "Final check"))

    def test_trk03_resumed_prompts_share_requested_type(self):
        main_with_agent_call(self.logs, subagent_type="developer")
        lines = [user("FIRST", 2), assistant("m1", 3)] + handback_pair("h1", "toolu_h1", 4)
        lines += [user("SECOND", 10, meta=True), assistant("m2", 11)]
        self.logs.sub("s1", "a1", lines, tool_use_id=SPEC_CALL)
        rows = [r for r in self.run_cli(["s1"]).kind("invocation") if r["role"] == "developer"]
        self.assertEqual(len(rows), 2)
        self.assertEqual({(r["requested_agent_type"], r["launched_by"]) for r in rows}, {("developer", "RUN-orchestrator-01")})


class CliErrorTest(TrackerCase):  # AC8, AC28
    def assert_nothing_written(self):
        self.assertFalse(self.md_path.exists())
        self.assertFalse(self.csv_path.exists())

    def test_trk03_no_logs_for_session_exit_2_exact_message(self):
        result = self.run_cli(["nothere"])
        self.assertEqual(result.code, 2)
        projects = str(self.logs.claude / "projects")
        self.assertEqual(
            result.err_lines(),
            [
                f'error: no Claude Code logs found for session ID "nothere" under {projects}: expected nothere.jsonl or '
                "nothere/subagents/agent-*.jsonl in a project folder (check the session ID and --claude-dir)"
            ],
        )
        self.assert_nothing_written()

    def test_trk03_duplicate_session_id_error(self):
        result = self.run_cli(["s1", "s2", "s1"])
        self.assertEqual(result.code, 2)
        self.assertEqual(
            result.err_lines(), ['error: session ID "s1" is given more than once (arguments 1 and 3): list each session once']
        )
        self.assert_nothing_written()

    def test_trk03_empty_session_id_error(self):
        result = self.run_cli(["s1", ""])
        self.assertEqual(result.code, 2)
        self.assertEqual(
            result.err_lines(), ["error: session ID argument 2 is empty: give a non-empty Claude Code session ID"]
        )
        self.assert_nothing_written()

    def test_trk03_invalid_run_id_error(self):
        self.logs.main("s1", [user("P", 0), assistant("m1", 1)])
        for bad in ("bad id!", ".lead", ""):
            result = self.run_cli(["s1"], run_id=bad) if bad else self.run_cli(["s1"], extra=["--run-id", ""])
            self.assertEqual(result.code, 2, bad)
            self.assertEqual(
                result.err_lines(),
                [
                    f'error: --run-id "{bad}" is invalid: it must start with a letter or digit and contain only letters, '
                    "digits, '.', '_' and '-'"
                ],
            )
        self.assert_nothing_written()

    def test_trk03_usage_errors_exit_2(self):
        self.assertEqual(self.run_cli([]).code, 2)

    def test_trk03_error_session_checks_run_in_the_documented_order(self):
        result = self.run_cli(["", "s1", "s1"], run_id="bad id")
        self.assertEqual(len(result.err_lines()), 1)
        self.assertIn("--run-id", result.err)
        result = self.run_cli(["", "s1", "s1"])
        self.assertIn("argument 1 is empty", result.err)

    def test_trk03_error_write_failure_names_option_and_path(self):
        self.logs.main("s1", [user("P", 0), assistant("m1", 1)])
        blocker = self.root / "blocker"
        blocker.write_text("file", encoding="utf-8")
        self.md_path = blocker / "report-v2.md"  # parent is a file, so it cannot be created
        result = self.run_cli(["s1"])
        self.assertEqual(result.code, 2)
        line = result.err_lines()[0]
        self.assertTrue(line.startswith(f'error: cannot write the report to --out-md "{self.md_path}": '), line)

    def test_trk03_errors_write_nothing_and_keep_existing_files(self):
        self.md_path.parent.mkdir(parents=True)
        self.md_path.write_text("OLD MD", encoding="utf-8")
        self.csv_path.write_text("OLD CSV", encoding="utf-8")
        self.assertEqual(self.run_cli(["nothere"]).code, 2)
        self.assertEqual(self.md_path.read_text(encoding="utf-8"), "OLD MD")
        self.assertEqual(self.csv_path.read_text(encoding="utf-8"), "OLD CSV")


if __name__ == "__main__":
    unittest.main()
