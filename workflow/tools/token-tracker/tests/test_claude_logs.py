import json
import tempfile
import unittest
from pathlib import Path

from helpers import claude_line, write_jsonl
from tracker.claude_logs import read_claude_rows


class ClaudeLogsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.project = self.root / "projects" / "C--proj"

    def test_duplicate_message_ids_keep_largest_output(self):  # AC1
        write_jsonl(
            self.project / "sess1.jsonl",
            [
                claude_line("m1", output=5),
                claude_line("m1", output=40),
                claude_line("m1", output=40),
                claude_line("m2", output=7),
            ],
        )
        rows = read_claude_rows(self.root)
        self.assertEqual(sorted(r.output_tokens for r in rows), [7, 40])

    def test_subagent_rows_carry_agent_type(self):  # AC2
        write_jsonl(self.project / "sess1.jsonl", [claude_line("m1")])
        sub = self.project / "sess1" / "subagents"
        write_jsonl(sub / "agent-abc.jsonl", [claude_line("s1", agent_id="abc", model="claude-opus-5-5")])
        (sub / "agent-abc.meta.json").write_text(
            json.dumps({"agentType": "verifier", "description": "x"}), encoding="utf-8"
        )
        rows = {r.agent_id or "main": r for r in read_claude_rows(self.root)}
        self.assertEqual(rows["main"].agent_type, "main")
        self.assertFalse(rows["main"].is_subagent)
        self.assertEqual(rows["abc"].agent_type, "verifier")
        self.assertTrue(rows["abc"].is_subagent)
        self.assertEqual(rows["abc"].model, "claude-opus-5-5")

    def test_subagent_without_meta_gets_unknown_type(self):  # AC2
        sub = self.project / "sess1" / "subagents"
        write_jsonl(sub / "agent-zzz.jsonl", [claude_line("s1", agent_id="zzz")])
        (row,) = read_claude_rows(self.root)
        self.assertEqual(row.agent_type, "unknown")

    def test_cache_creation_split(self):  # AC3
        write_jsonl(
            self.project / "sess1.jsonl",
            [
                claude_line("m1", cache_create=30, breakdown=(10, 20)),
                claude_line("m2", cache_create=30, breakdown=None),
            ],
        )
        by_id = sorted(read_claude_rows(self.root), key=lambda r: r.cache_write_1h_tokens)
        self.assertEqual((by_id[0].cache_write_5m_tokens, by_id[0].cache_write_1h_tokens), (30, 0))
        self.assertEqual((by_id[1].cache_write_5m_tokens, by_id[1].cache_write_1h_tokens), (10, 20))

    def test_skips_bad_lines_and_synthetic(self):  # AC4
        write_jsonl(
            self.project / "sess1.jsonl",
            [
                "{not json",
                {"type": "user", "message": {"role": "user", "content": "hi"}},
                claude_line("syn", model="<synthetic>"),
                claude_line("ok", output=3),
            ],
        )
        rows = read_claude_rows(self.root)
        self.assertEqual([r.output_tokens for r in rows], [3])

    def test_row_fields(self):
        write_jsonl(
            self.project / "sess1.jsonl",
            [claude_line("m1", inp=4, cache_read=9, output=11, thinking=6, branch="exp/b", cwd="C:\\x")],
        )
        (row,) = read_claude_rows(self.root)
        self.assertEqual(row.tool, "claude")
        self.assertEqual(row.session_id, "sess1")
        self.assertEqual(row.branch, "exp/b")
        self.assertEqual(row.cwd, "C:\\x")
        self.assertEqual(
            (row.input_tokens, row.cache_read_tokens, row.output_tokens, row.reasoning_tokens),
            (4, 9, 11, 6),
        )

    def test_missing_directory_gives_no_rows(self):
        self.assertEqual(read_claude_rows(self.root / "nope"), [])


if __name__ == "__main__":
    unittest.main()
