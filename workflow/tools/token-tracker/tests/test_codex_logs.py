import tempfile
import unittest
from pathlib import Path

from helpers import codex_meta, codex_session, codex_tokens, codex_turn
from tracker.codex_logs import read_codex_rows


class CodexLogsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.day = self.root / "sessions" / "2026" / "10" / "29"

    def test_token_count_becomes_row_with_uncached_input(self):  # AC5
        codex_session(
            self.day / "rollout-a.jsonl",
            [codex_meta(), codex_turn("gpt-x"), codex_tokens(1000, 400, 50, 30, total=1050)],
        )
        (row,) = read_codex_rows(self.root)
        self.assertEqual(row.tool, "codex")
        self.assertEqual(row.model, "gpt-x")
        self.assertEqual(row.input_tokens, 600)
        self.assertEqual(row.cache_read_tokens, 400)
        self.assertEqual(row.output_tokens, 50)
        self.assertEqual(row.reasoning_tokens, 30)
        self.assertEqual(row.branch, "exp/a")
        self.assertFalse(row.is_subagent)

    def test_repeated_cumulative_total_is_skipped(self):  # AC5
        codex_session(
            self.day / "rollout-a.jsonl",
            [
                codex_meta(),
                codex_turn(),
                codex_tokens(100, 0, 10, 0, total=110),
                codex_tokens(100, 0, 10, 0, total=110),
                codex_tokens(200, 50, 20, 5, total=330),
            ],
        )
        rows = read_codex_rows(self.root)
        self.assertEqual([r.output_tokens for r in rows], [10, 20])

    def test_model_follows_latest_turn_context(self):  # AC5
        codex_session(
            self.day / "rollout-a.jsonl",
            [
                codex_meta(),
                codex_turn("m1"),
                codex_tokens(10, 0, 1, 0, total=11),
                codex_turn("m2"),
                codex_tokens(10, 0, 2, 0, total=23),
            ],
        )
        self.assertEqual([r.model for r in read_codex_rows(self.root)], ["m1", "m2"])

    def test_parent_thread_marks_subagent(self):  # AC5
        codex_session(
            self.day / "rollout-b.jsonl",
            [codex_meta(session_id="c2", parent="c1"), codex_turn(), codex_tokens(10, 0, 1, 0, total=11)],
        )
        (row,) = read_codex_rows(self.root)
        self.assertTrue(row.is_subagent)
        self.assertEqual(row.agent_type, "subagent")
        self.assertEqual(row.session_id, "c2")

    def test_events_without_info_and_bad_lines_skipped(self):  # AC4
        codex_session(
            self.day / "rollout-a.jsonl",
            [
                "{broken",
                codex_meta(),
                {"type": "event_msg", "payload": {"type": "token_count", "info": None}},
                codex_turn(),
                codex_tokens(10, 0, 1, 0, total=11),
            ],
        )
        self.assertEqual(len(read_codex_rows(self.root)), 1)

    def test_missing_directory_gives_no_rows(self):
        self.assertEqual(read_codex_rows(self.root / "nope"), [])


if __name__ == "__main__":
    unittest.main()
