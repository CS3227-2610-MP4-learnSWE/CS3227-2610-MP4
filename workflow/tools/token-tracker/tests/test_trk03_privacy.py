import re
import unittest

from helpers_trk03 import TrackerCase, assistant, result, tu, user

SENTINEL = re.compile(r"SENTINEL_[A-Z_]+_7f3a")


def text_block(text):
    return {"type": "text", "text": text}


class PrivacyTest(TrackerCase):
    """Sentinels in every free-text place of a log must never reach any output."""

    def setUp(self):
        super().setUp()
        main_blocks = [
            text_block("SENTINEL_REPLY_7f3a"),
            {"type": "thinking", "thinking": "SENTINEL_THINKING_7f3a"},
            tu("A1", "Agent", subagent_type="developer", description="SENTINEL_AGENT_DESC_7f3a", prompt="SENTINEL_AGENT_PROMPT_7f3a"),
            tu("A2", "Agent", subagent_type="SENTINEL_ODD_7f3a with spaces", description="SENTINEL_AGENT_DESC_7f3a", prompt="SENTINEL_AGENT_PROMPT_7f3a"),
        ]
        self.logs.main("s1", [user("SENTINEL_PROMPT_7f3a", 0), assistant("om1", 1, main_blocks)])
        sub_blocks = [
            tu("b1", "Bash", command="SENTINEL_BASH_7f3a"),
            tu("g1", "Grep", pattern="SENTINEL_GREP_7f3a", path="C:/r"),
            tu("w1", "Write", file_path="C:/r/w.py", content="SENTINEL_WRITE_7f3a"),
            tu("e1", "Edit", file_path="C:/r/e.py", old_string="SENTINEL_OLD_7f3a", new_string="SENTINEL_EDIT_7f3a"),
            tu("r1", "Read", file_path="C:/r/a.py"),
            tu("r2", "Read", file_path="C:/r/a.py"),
        ]
        self.logs.sub(
            "s1", "a1",
            [user("SENTINEL_PROMPT_7f3a", 2), assistant("m1", 3, sub_blocks), result("b1", 4, text="SENTINEL_RESULT_7f3a"),
             result("r1", 5, text="SENTINEL_FILE_7f3a contents"), user("SENTINEL_HUMAN_7f3a", 6)],
            tool_use_id="A1", description="SENTINEL_META_DESC_7f3a",
        )
        self.logs.sub("s1", "a2", [user("SENTINEL_PROMPT_7f3a", 7), assistant("m2", 8, [text_block("SENTINEL_REPLY_7f3a")])],
                      tool_use_id="A2", description="SENTINEL_META_DESC_7f3a")
        self.logs.sub("s1", "a3", [user("SENTINEL_PROMPT_7f3a", 9), assistant("m3", 10)], meta=False)

    def everything(self, outcome):
        parts = [outcome.out, outcome.err]
        for path in (self.md_path, self.csv_path):
            if path.exists():
                parts.append(path.read_text(encoding="utf-8"))
        return "\n".join(parts)

    def test_trk03_privacy_no_sentinel_in_markdown_csv_stdout(self):  # AC22
        outcome = self.run_cli(["s1"])
        self.assertEqual(outcome.code, 0, outcome.err)
        self.assertEqual(SENTINEL.findall(self.everything(outcome)), [])
        self.assertIn("RUN-developer-01", outcome.md)

    def test_trk03_privacy_no_sentinel_in_errors_and_warnings(self):  # AC22
        outcome = self.run_cli(["s1"])
        self.assertTrue(outcome.err.startswith("warning: agent a3 in session s1"))
        self.assertEqual(SENTINEL.findall(outcome.err), [])
        self.logs.stray("s1", [{"agentId": "a1", **assistant("m1", 3, [text_block("SENTINEL_REPLY_7f3a")], out=999)}])
        mismatch = self.run_cli(["s1"])
        self.assertEqual(mismatch.code, 1)
        self.assertEqual(SENTINEL.findall(self.everything(mismatch)), [])
        for sessions, meta in ((["missing"], None), (["s1"], self.write_meta(["RUN-nope-01,,,,,,,,"]))):
            failure = self.run_cli(sessions, meta=meta)
            self.assertEqual(failure.code, 2)
            self.assertEqual(SENTINEL.findall(self.everything(failure)), [])

    def test_trk03_read_path_may_appear_other_tool_inputs_not(self):  # AC22
        outcome = self.run_cli(["s1"])
        row = outcome.inv("RUN-developer-01")
        self.assertEqual(row["repeated_paths"], "c:/r/a.py")
        self.assertEqual(row["tool_calls_by_name"], "Bash=1; Edit=1; Grep=1; Read=2; Write=1")
        for forbidden in ("w.py", "e.py", "C:/r;", "SENTINEL"):
            self.assertNotIn(forbidden, outcome.csv_text, forbidden)

    def test_trk03_agent_call_description_and_prompt_not_in_output(self):  # AC22
        outcome = self.run_cli(["s1"])
        self.assertEqual(outcome.inv("RUN-developer-01")["requested_agent_type"], "developer")
        self.assertEqual(outcome.inv("RUN-developer-02")["requested_agent_type"], "unavailable")
        self.assertNotIn("SENTINEL_ODD", self.everything(outcome))
        self.assertNotIn("spaces", self.everything(outcome))


if __name__ == "__main__":
    unittest.main()
