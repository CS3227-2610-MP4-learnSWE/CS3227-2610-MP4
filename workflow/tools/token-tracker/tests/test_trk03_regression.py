"""AC24: existing commands behave as before the TRK-03 change (goldens captured from the unmodified code)."""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from helpers import claude_line, write_jsonl
from tracker.cli import main

RUN_ID = "2026-11-05-REG-01"
PRICES = {
    "models": {
        "claude-sonnet-5-5": {"input": 2.0, "cache_write_5m": 2.5, "cache_write_1h": 4.0, "cache_read": 0.1, "output": 10.0},
        "claude-opus-5-5": {"input": 4.0, "cache_write_5m": 5.0, "cache_write_1h": 8.0, "cache_read": 0.2, "output": 20.0},
    }
}
MANIFEST = (
    "feature_run_id,invocation_id,role,effort,tool,session_id,agent_id,started_at,finished_at\n"
    f"{RUN_ID},{RUN_ID}-orchestrator-01,orchestrator,high,claude,sess1,,2026-10-29T00:59:00+00:00,2026-10-29T01:10:00+00:00\n"
    f"{RUN_ID},{RUN_ID}-verifier-01,verifier,high,claude,sess1,abc,2026-10-29T01:01:00+00:00,2026-10-29T01:05:00+00:00\n"
)


def build(root: Path):
    project = root / "claude" / "projects" / "C--proj"
    write_jsonl(
        project / "sess1.jsonl",
        [
            claude_line("m1", output=7, ts="2026-10-29T01:00:00.000Z"),
            claude_line("m1", output=40, ts="2026-10-29T01:00:00.000Z"),
            claude_line("m2", output=9, ts="2026-10-29T01:09:00.000Z", model="claude-opus-5-5", thinking=4),
        ],
    )
    sub = project / "sess1" / "subagents"
    write_jsonl(sub / "agent-abc.jsonl", [claude_line("s1", agent_id="abc", output=21, ts="2026-10-29T01:02:00.000Z")])
    (sub / "agent-abc.meta.json").write_text(json.dumps({"agentType": "verifier", "description": "x"}), encoding="utf-8")
    (root / "codex").mkdir()
    prices = root / "prices.json"
    prices.write_text(json.dumps(PRICES), encoding="utf-8")
    run_dir = root / RUN_ID
    run_dir.mkdir()
    (run_dir / "invocations.csv").write_text(MANIFEST, encoding="utf-8")
    return prices, run_dir


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue()


GOLDEN_REPORT = 'agent_type  model              requests  input_tokens  cache_read_tokens  cache_write_5m_tokens  cache_write_1h_tokens  output_tokens  reasoning_tokens  cost_usd\nmain        claude-opus-5-5    1         2             100                50                     0                      9              4                 0.000458\nmain        claude-sonnet-5-5  1         2             100                50                     0                      40             0                 0.000539\nverifier    claude-sonnet-5-5  1         2             100                50                     0                      21             0                 0.000349\nTOTAL                          3         6             300                150                    0                      70             4                 0.001346\n'
GOLDEN_EXPORT = 'tool,session_id,agent_id,agent_type,is_subagent,model,branch,cwd,timestamp,input_tokens,cache_read_tokens,cache_write_5m_tokens,cache_write_1h_tokens,output_tokens,reasoning_tokens,cost_usd\nclaude,sess1,,main,false,claude-sonnet-5-5,exp/a,C:\\proj,2026-10-29T01:00:00.000Z,2,100,50,0,40,0,0.000539\nclaude,sess1,abc,verifier,true,claude-sonnet-5-5,exp/a,C:\\proj,2026-10-29T01:02:00.000Z,2,100,50,0,21,0,0.000349\nclaude,sess1,,main,false,claude-opus-5-5,exp/a,C:\\proj,2026-10-29T01:09:00.000Z,2,100,50,0,9,4,0.000458\n'
GOLDEN_RUN_REPORT = '# Feature-run report: 2026-11-05-REG-01\n\nFormat: `invocation-v1`\n\nElapsed values are wall-clock durations. The run total is latest finish minus earliest start, so parallel agent time is not added twice.\n\nToken usage = uncached input + cache reads + cache writes + output. Reasoning is already included in output and is not added again. Unmatched usage and incomplete totals are unavailable, not zero.\n\n| Record | Feature run ID | Invocation ID | Role | Model(s) | Effort | Elapsed | Requests | Token usage | Cost (USD) |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n| invocation | 2026-11-05-REG-01 | 2026-11-05-REG-01-orchestrator-01 | orchestrator | claude-opus-5-5; claude-sonnet-5-5 | high | 0:11:00 | 2 | 353 | 0.000997 |\n| invocation | 2026-11-05-REG-01 | 2026-11-05-REG-01-verifier-01 | verifier | claude-sonnet-5-5 | high | 0:04:00 | 1 | 173 | 0.000349 |\n| feature_run_total | 2026-11-05-REG-01 |  | TOTAL | claude-opus-5-5; claude-sonnet-5-5 |  | 0:11:00 | 3 | 526 | 0.001346 |\n'


class RegressionTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.prices, self.run_dir = build(self.root)
        self.common = ["--claude-dir", str(self.root / "claude"), "--codex-dir", str(self.root / "codex"), "--prices", str(self.prices)]

    def test_trk03_report_and_export_unchanged(self):  # AC24
        code, table = run(["report", *self.common])
        self.assertEqual(code, 0)
        self.assertEqual(table.replace("\r\n", "\n"), GOLDEN_REPORT)
        target = self.root / "usage.csv"
        code, _ = run(["export", *self.common, "--out", str(target)])
        self.assertEqual(code, 0)
        self.assertEqual(target.read_text(encoding="utf-8"), GOLDEN_EXPORT)

    def test_run_report_single_token_column_amendment(self):  # User amendment 2026-11-07
        code, line = run(["run-report", "--manifest", str(self.run_dir / "invocations.csv"), *self.common])
        self.assertEqual(code, 0)
        self.assertTrue(line.startswith(f"Wrote feature-run report for {RUN_ID} (2 invocations) to "))
        self.assertEqual((self.run_dir / "report.md").read_text(encoding="utf-8"), GOLDEN_RUN_REPORT)


if __name__ == "__main__":
    unittest.main()
