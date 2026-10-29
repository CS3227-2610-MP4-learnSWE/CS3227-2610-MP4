"""Builders for synthetic Claude Code and Codex log files used by the tests."""

import json
from pathlib import Path

SECRET = "SECRET_PROMPT_TEXT"


def write_jsonl(path: Path, objects: list) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [o if isinstance(o, str) else json.dumps(o) for o in objects]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def claude_line(
    msg_id,
    output=10,
    model="claude-sonnet-5-5",
    session="sess1",
    agent_id=None,
    branch="exp/a",
    cwd="C:\\proj",
    ts="2026-10-29T01:00:00.000Z",
    inp=2,
    cache_read=100,
    cache_create=50,
    breakdown=(50, 0),
    thinking=0,
):
    usage = {
        "input_tokens": inp,
        "cache_creation_input_tokens": cache_create,
        "cache_read_input_tokens": cache_read,
        "output_tokens": output,
        "output_tokens_details": {"thinking_tokens": thinking},
    }
    if breakdown is not None:
        usage["cache_creation"] = {
            "ephemeral_5m_input_tokens": breakdown[0],
            "ephemeral_1h_input_tokens": breakdown[1],
        }
    line = {
        "isSidechain": agent_id is not None,
        "type": "assistant",
        "sessionId": session,
        "gitBranch": branch,
        "cwd": cwd,
        "timestamp": ts,
        "message": {
            "id": msg_id,
            "model": model,
            "role": "assistant",
            "content": [{"type": "text", "text": SECRET}],
            "usage": usage,
        },
    }
    if agent_id is not None:
        line["agentId"] = agent_id
    return line


def codex_session(path: Path, events: list) -> Path:
    return write_jsonl(path, events)


def codex_meta(session_id="c1", cwd="C:\\proj", branch="exp/a", parent=None):
    payload = {
        "id": session_id,
        "cwd": cwd,
        "git": {"branch": branch} if branch else {},
        "timestamp": "2026-10-29T02:00:00.000Z",
    }
    if parent:
        payload["parent_thread_id"] = parent
    return {"type": "session_meta", "payload": payload}


def codex_turn(model="gpt-test"):
    return {"type": "turn_context", "payload": {"model": model}}


def codex_tokens(inp, cached, output, reasoning, total, ts="2026-10-29T02:00:05.000Z"):
    last = {
        "input_tokens": inp,
        "cached_input_tokens": cached,
        "cache_write_input_tokens": 0,
        "output_tokens": output,
        "reasoning_output_tokens": reasoning,
        "total_tokens": total,
    }
    return {
        "type": "event_msg",
        "timestamp": ts,
        "payload": {
            "type": "token_count",
            "info": {
                "total_token_usage": {"total_tokens": total},
                "last_token_usage": last,
            },
        },
    }
