"""Parse Codex rollout logs into usage rows."""

from __future__ import annotations

from pathlib import Path

from .jsonl import as_int, read_objects
from .model import UsageRow


def read_codex_rows(codex_dir: Path) -> list[UsageRow]:
    """Return one row per `token_count` event whose cumulative total changed."""
    sessions = Path(codex_dir) / "sessions"
    if not sessions.is_dir():
        return []
    rows: list[UsageRow] = []
    for path in sorted(sessions.rglob("rollout-*.jsonl")):
        rows.extend(_rows_from_rollout(path))
    return rows


def _rows_from_rollout(path: Path) -> list[UsageRow]:
    session_id, cwd, branch, parent, started = path.stem, "", "", "", ""
    model, last_total = "", None
    rows: list[UsageRow] = []
    for obj in read_objects(path):
        payload = obj.get("payload")
        if not isinstance(payload, dict):
            continue
        kind = obj.get("type")
        if kind == "session_meta":
            session_id = payload.get("id") or session_id
            cwd = payload.get("cwd") or ""
            branch = (payload.get("git") or {}).get("branch") or ""
            parent = payload.get("parent_thread_id") or ""
            started = payload.get("timestamp") or ""
        elif kind == "turn_context":
            model = payload.get("model") or model
        elif kind == "event_msg" and payload.get("type") == "token_count":
            info = payload.get("info")
            if not isinstance(info, dict):
                continue
            total = (info.get("total_token_usage") or {}).get("total_tokens")
            if total is None or total == last_total:
                continue
            last_total = total
            usage = info.get("last_token_usage") or {}
            cached = as_int(usage.get("cached_input_tokens"))
            is_subagent = bool(parent)
            rows.append(
                UsageRow(
                    tool="codex",
                    session_id=session_id,
                    agent_id=session_id if is_subagent else "",
                    agent_type="subagent" if is_subagent else "main",
                    is_subagent=is_subagent,
                    model=model,
                    branch=branch,
                    cwd=cwd,
                    timestamp=obj.get("timestamp") or started,
                    input_tokens=max(as_int(usage.get("input_tokens")) - cached, 0),
                    cache_read_tokens=cached,
                    cache_write_5m_tokens=as_int(usage.get("cache_write_input_tokens")),
                    cache_write_1h_tokens=0,
                    output_tokens=as_int(usage.get("output_tokens")),
                    reasoning_tokens=as_int(usage.get("reasoning_output_tokens")),
                )
            )
    return rows
