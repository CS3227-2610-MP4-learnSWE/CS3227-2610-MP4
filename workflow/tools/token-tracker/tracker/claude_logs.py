"""Parse Claude Code session logs, including subagent files, into usage rows."""

from __future__ import annotations

import json
from pathlib import Path

from .jsonl import as_int, read_objects
from .model import UsageRow

SYNTHETIC_MODEL = "<synthetic>"


def read_claude_rows(claude_dir: Path) -> list[UsageRow]:
    """Return one row per distinct assistant message under `<claude_dir>/projects`."""
    projects = Path(claude_dir) / "projects"
    if not projects.is_dir():
        return []
    best: dict[tuple, UsageRow] = {}
    for path in sorted(projects.rglob("*.jsonl")):
        agent_type = _agent_type(path)
        for obj in read_objects(path):
            parsed = _row_from_line(obj, path, agent_type)
            if parsed is None:
                continue
            key, row = parsed
            kept = best.get(key)
            if kept is None or row.output_tokens >= kept.output_tokens:
                best[key] = row
    return list(best.values())


def _agent_type(path: Path) -> str:
    """Subagent type from the sibling `.meta.json`, else `unknown`; `main` outside `subagents/`."""
    if path.parent.name != "subagents":
        return "main"
    try:
        meta = json.loads(path.with_suffix(".meta.json").read_text(encoding="utf-8"))
        return str(meta.get("agentType") or "unknown")
    except (OSError, ValueError):
        return "unknown"


def _row_from_line(obj: dict, path: Path, agent_type: str):
    message = obj.get("message")
    if not isinstance(message, dict):
        return None
    usage = message.get("usage")
    model = message.get("model") or ""
    if not isinstance(usage, dict) or not model or model == SYNTHETIC_MODEL:
        return None
    message_id = message.get("id") or obj.get("uuid") or ""
    agent_id = obj.get("agentId") or ""
    session_id = obj.get("sessionId") or path.stem
    is_subagent = bool(agent_id) or bool(obj.get("isSidechain"))
    write_5m, write_1h = _cache_writes(usage)
    row = UsageRow(
        tool="claude",
        session_id=session_id,
        agent_id=agent_id,
        agent_type=agent_type if is_subagent else "main",
        is_subagent=is_subagent,
        model=model,
        branch=obj.get("gitBranch") or "",
        cwd=obj.get("cwd") or "",
        timestamp=obj.get("timestamp") or "",
        input_tokens=as_int(usage.get("input_tokens")),
        cache_read_tokens=as_int(usage.get("cache_read_input_tokens")),
        cache_write_5m_tokens=write_5m,
        cache_write_1h_tokens=write_1h,
        output_tokens=as_int(usage.get("output_tokens")),
        reasoning_tokens=as_int((usage.get("output_tokens_details") or {}).get("thinking_tokens")),
    )
    return (session_id, agent_id, message_id), row


def _cache_writes(usage: dict) -> tuple[int, int]:
    """Split cache creation into 5-minute and 1-hour tokens when the log says how."""
    breakdown = usage.get("cache_creation")
    if isinstance(breakdown, dict) and breakdown:
        return (
            as_int(breakdown.get("ephemeral_5m_input_tokens")),
            as_int(breakdown.get("ephemeral_1h_input_tokens")),
        )
    return as_int(usage.get("cache_creation_input_tokens")), 0


