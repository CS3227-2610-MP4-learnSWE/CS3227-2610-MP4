"""Synthetic Claude Code session builders for the TRK-03 tests. No real logs are used."""

import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tracker.cli import main

BASE = datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc)

PRICES = {
    "as_of": "2026-10-29",
    "models": {
        "claude-sonnet-5-5": {"input": 2.0, "cache_write_5m": 2.5, "cache_write_1h": 4.0, "cache_read": 0.1, "output": 10.0},
        "claude-haiku-5-5": {
            "match_variants": True,
            "tiers": [
                {"max_prompt_tokens": 100000, "input": 0.10, "cache_write_5m": 0.125, "cache_write_1h": 0.20, "cache_read": 0.01, "output": 0.50},
                {"input": 0.50, "cache_write_5m": 0.625, "cache_write_1h": 1.00, "cache_read": 0.05, "output": 2.50},
            ],
        },
    },
}


def T(seconds):
    """ISO UTC timestamp `seconds` after the base time (millisecond precision)."""
    moment = BASE + timedelta(seconds=seconds)
    return moment.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def user(text, t=None, meta=False, prompt_id=None):
    line = {"type": "user", "message": {"role": "user", "content": text}}
    if t is not None:
        line["timestamp"] = T(t)
    if meta:
        line["isMeta"] = True
    if prompt_id:
        line["promptId"] = prompt_id
    return line


def tu(tool_id, name, **tool_input):
    return {"type": "tool_use", "id": tool_id, "name": name, "input": tool_input}


def assistant(
    mid, t=None, blocks=(), model="claude-sonnet-5-5", requested="same", inp=10, cr=0, w5=0, w1=0, out=5, thinking=0,
):
    """One log line of an assistant message; call twice with one `mid` to simulate a block logged on several lines."""
    usage = {
        "input_tokens": inp,
        "cache_creation_input_tokens": w5 + w1,
        "cache_read_input_tokens": cr,
        "output_tokens": out,
        "cache_creation": {"ephemeral_5m_input_tokens": w5, "ephemeral_1h_input_tokens": w1},
    }
    if thinking is not None:
        usage["output_tokens_details"] = {"thinking_tokens": thinking}
    line = {
        "type": "assistant",
        "message": {
            "id": mid,
            "model": model,
            "role": "assistant",
            "content": [{"type": "text", "text": "reply"}, *blocks],
            "usage": usage,
        },
    }
    if requested == "same":
        line["requestedModel"] = model
    elif requested is not None:
        line["requestedModel"] = requested
    if t is not None:
        line["timestamp"] = T(t)
    return line


def result(tool_id, t=None, is_error=False, text="ok"):
    block = {"type": "tool_result", "tool_use_id": tool_id, "content": text}
    if is_error:
        block["is_error"] = True
    line = {"type": "user", "message": {"role": "user", "content": [block]}, "toolUseResult": {"stdout": text}}
    if t is not None:
        line["timestamp"] = T(t)
    return line


def handback_pair(mid, tool_id, t):
    """An assistant SubagentHandback call and its result: the end of one prompt."""
    return [assistant(mid, t, [tu(tool_id, "SubagentHandback", message="done")]), result(tool_id, t + 0.5)]


class Logs:
    """A temporary Claude directory (`<root>/claude/projects/...`) plus an empty Codex directory."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.claude = self.root / "claude"
        self.codex = self.root / "codex"
        self.codex.mkdir(parents=True, exist_ok=True)
        (self.claude / "projects").mkdir(parents=True, exist_ok=True)

    def _write(self, path: Path, lines):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(json.dumps(line) for line in lines) + "\n", encoding="utf-8")

    def main(self, session, lines, project="projA"):
        stamped = [{"sessionId": session, **line} for line in lines]
        self._write(self.claude / "projects" / project / f"{session}.jsonl", stamped)

    def sub(self, session, agent, lines, agent_type="developer", tool_use_id="", description="d", project="projA", meta=True):
        stamped = [{"sessionId": session, "agentId": agent, "isSidechain": True, **line} for line in lines]
        folder = self.claude / "projects" / project / session / "subagents"
        self._write(folder / f"agent-{agent}.jsonl", stamped)
        if meta:
            body = {"agentType": agent_type, "description": description, "finished": True, "toolUseId": tool_use_id}
            (folder / f"agent-{agent}.meta.json").write_text(json.dumps(body), encoding="utf-8")

    def stray(self, session, lines, name="stray.jsonl", project="projOther"):
        """A log of `session` stored outside the session folder layout."""
        stamped = [{"sessionId": session, **line} for line in lines]
        self._write(self.claude / "projects" / project / name, stamped)


class Result:
    def __init__(self, code, out, err, md_path, csv_path):
        self.code, self.out, self.err, self.md_path, self.csv_path = code, out, err, md_path, csv_path

    @property
    def md(self):
        return self.md_path.read_text(encoding="utf-8")

    @property
    def csv_text(self):
        return self.csv_path.read_text(encoding="utf-8")

    def rows(self):
        return list(csv.DictReader(io.StringIO(self.csv_text)))

    def kind(self, record):
        return [r for r in self.rows() if r["record"] == record]

    def inv(self, invocation_id=None):
        rows = self.kind("invocation")
        if invocation_id is None:
            return rows[0] if len(rows) == 1 else rows
        return next(r for r in rows if r["invocation_id"] == invocation_id)

    def err_lines(self):
        return [line for line in self.err.splitlines() if line]


class TrackerCase(unittest.TestCase):
    RUN = "RUN"

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.logs = Logs(self.root / "logs")
        self.prices_path = self.root / "prices.json"
        self.prices_path.write_text(json.dumps(PRICES), encoding="utf-8")
        self.md_path = self.root / "out" / "report-v2.md"
        self.csv_path = self.root / "out" / "metrics-v2.csv"

    def run_cli(self, sessions, run_id=None, meta=None, extra=(), prices=True, default_paths=False):
        argv = ["invocations-from-logs", "--run-id", run_id or self.RUN]
        argv += ["--claude-dir", str(self.logs.claude), "--codex-dir", str(self.logs.codex)]
        argv += ["--prices", str(self.prices_path if prices else self.root / "no-prices.json")]
        if not default_paths:
            argv += ["--out-md", str(self.md_path), "--out-csv", str(self.csv_path)]
        if meta is not None:
            argv += ["--meta", str(meta)]
        argv += list(extra) + list(sessions)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            try:
                code = main(argv)
            except SystemExit as exc:  # argparse usage errors
                code = exc.code
        return Result(code, out.getvalue(), err.getvalue(), self.md_path, self.csv_path)

    def write_meta(self, rows, header=None):
        header = header or "invocation_id,role_label,arm,phase,revision_round,trigger,start_commit,end_commit,agent_definition_hash"
        path = self.root / "meta.csv"
        path.write_text(header + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
        return path

    def one_sub(self, requests, session="s1", agent="a1", agent_type="developer", prompt_t=0):
        """A single subagent file with a prompt line then `requests` (assistant/user/result lines)."""
        lines = [user("PROMPT", prompt_t)] + list(requests)
        self.logs.sub(session, agent, lines, agent_type=agent_type)
        return self.run_cli([session])
