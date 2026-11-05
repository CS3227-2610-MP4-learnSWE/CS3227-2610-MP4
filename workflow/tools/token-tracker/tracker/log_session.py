"""Read one Claude Code log file into prompt windows: requests, tool calls, times and human messages.

Only structure is kept. Tool inputs are reduced to the tool name and, for `Read`, the normalised file path;
no prompt, reply, tool result or file content is stored.
"""

from __future__ import annotations

import posixpath
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .claude_logs import agent_meta, keep_largest, row_from_line
from .jsonl import read_objects
from .model import UsageRow
from .timeutil import parse_utc

_AGENT_TYPE = re.compile(r"[A-Za-z0-9._:-]{1,64}")
HANDBACK_TOOL = "SubagentHandback"


@dataclass(frozen=True)
class RequestInfo:
    row: UsageRow  # unpriced
    order: int  # line index where this message id first appeared in its file
    requested_model: str  # top-level requestedModel of the kept line, "" if absent
    reasoning_reported: bool  # kept line has output_tokens_details.thinking_tokens as an int


@dataclass(frozen=True)
class ToolCallInfo:
    tool_use_id: str
    name: str
    use_time: datetime | None  # time of the first line holding this tool_use
    result_time: datetime | None  # time of the first user line with a tool_result for this id
    is_error: bool  # any matching tool_result block has is_error is True
    read_path: str | None  # normalised path when name == "Read" and input.file_path is a non-empty str


@dataclass(frozen=True)
class WindowLog:
    requests: tuple[RequestInfo, ...]
    tool_calls: tuple[ToolCallInfo, ...]
    first_time: datetime | None
    last_time: datetime | None
    human_messages: int


@dataclass(frozen=True)
class FileLog:
    path: Path
    agent_id: str  # "" for the main file, X for agent-X.jsonl
    meta: dict | None
    windows: tuple[WindowLog, ...]
    agent_calls: Mapping[str, str | None]  # Agent tool_use id -> subagent_type if it is a short plain name, else None


def find_session_files(claude_dir: Path, session_id: str) -> tuple[Path | None, list[Path]]:
    """The main file and the subagent files of a session, found by name in every project folder."""
    projects = Path(claude_dir) / "projects"
    main: Path | None = None
    subagents: list[Path] = []
    if not projects.is_dir():
        return None, subagents
    for path in sorted(projects.rglob("*.jsonl")):
        if path.parent.name == "subagents":
            if path.name.startswith("agent-") and path.parent.parent.name == session_id:
                subagents.append(path)
        elif main is None and path.name == f"{session_id}.jsonl":
            main = path
    return main, subagents


def normalise_read_path(raw: str) -> str:
    """Trim, use `/`, collapse `.` and `..`, lowercase a leading drive letter."""
    path = posixpath.normpath(raw.strip().replace("\\", "/"))
    if len(path) >= 2 and path[1] == ":" and path[0].isalpha():
        path = path[0].lower() + path[1:]
    return path


class _Window:
    def __init__(self) -> None:
        self.keys: list[tuple] = []
        self.call_ids: list[str] = []
        self.first: datetime | None = None
        self.last: datetime | None = None
        self.human = 0

    def see(self, moment: datetime | None) -> None:
        if moment is None:
            return
        if self.first is None or moment < self.first:
            self.first = moment
        if self.last is None or moment > self.last:
            self.last = moment


def read_file_log(path: Path, agent_type: str, split_prompts: bool) -> FileLog:
    """Parse one log file. `split_prompts` opens a new window after each `SubagentHandback` result."""
    is_subagent = path.parent.name == "subagents" and path.name.startswith("agent-")
    agent_id = path.stem[len("agent-") :] if is_subagent else ""
    windows = [_Window()]
    best: dict[tuple, UsageRow] = {}
    details: dict[tuple, list] = {}  # key -> [order, requested model, reasoning reported]
    calls: dict[str, dict] = {}
    results: dict[str, dict] = {}
    handback_ids: set[str] = set()
    agent_calls: dict[str, str | None] = {}
    pending_handback = False
    prompt_seen = False

    for index, obj in enumerate(read_objects(path)):
        message = obj.get("message") if isinstance(obj.get("message"), dict) else {}
        content = message.get("content")
        is_meta = obj.get("isMeta") is True
        if obj.get("type") == "user" and isinstance(content, str):
            if split_prompts and pending_handback:
                windows.append(_Window())
                pending_handback = False
                prompt_seen = True
            elif not is_meta and not prompt_seen:
                prompt_seen = True
            elif not is_meta:
                windows[-1].human += 1
        window = windows[-1]
        window.see(parse_utc(obj.get("timestamp")))

        parsed = row_from_line(obj, path, agent_type)
        if parsed is not None:
            key, row = parsed
            keep_largest(best, key, row)
            if key not in details:
                details[key] = [index, "", False]
                window.keys.append(key)
            if best[key] is row:
                reasoning = (message.get("usage") or {}).get("output_tokens_details")
                reasoning = reasoning.get("thinking_tokens") if isinstance(reasoning, dict) else None
                details[key][1] = obj.get("requestedModel") if isinstance(obj.get("requestedModel"), str) else ""
                details[key][2] = isinstance(reasoning, int) and not isinstance(reasoning, bool)

        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if obj.get("type") == "assistant" and block.get("type") == "tool_use":
                _record_tool_use(block, window, calls, handback_ids, agent_calls, parse_utc(obj.get("timestamp")))
            elif obj.get("type") == "user" and block.get("type") == "tool_result":
                tool_id = block.get("tool_use_id")
                if not isinstance(tool_id, str):
                    continue
                seen = results.setdefault(tool_id, {"time": parse_utc(obj.get("timestamp")), "error": False})
                seen["error"] = seen["error"] or block.get("is_error") is True
                if tool_id in handback_ids:
                    pending_handback = True

    return FileLog(
        path=path,
        agent_id=agent_id,
        meta=agent_meta(path) if is_subagent else None,
        windows=tuple(_freeze(w, best, details, calls, results) for w in windows),
        agent_calls=agent_calls,
    )


def _record_tool_use(block, window, calls, handback_ids, agent_calls, moment) -> None:
    tool_id, name = block.get("id"), block.get("name")
    if not isinstance(tool_id, str) or not isinstance(name, str) or tool_id in calls:
        return
    tool_input = block.get("input") if isinstance(block.get("input"), dict) else {}
    read_path = None
    if name == "Read":
        raw = tool_input.get("file_path")
        if isinstance(raw, str) and raw.strip():
            read_path = normalise_read_path(raw)
    if name == "Agent":
        kind = tool_input.get("subagent_type")
        agent_calls[tool_id] = kind if isinstance(kind, str) and _AGENT_TYPE.fullmatch(kind) else None
    if name == HANDBACK_TOOL:
        handback_ids.add(tool_id)
    calls[tool_id] = {"name": name, "time": moment, "read_path": read_path}
    window.call_ids.append(tool_id)


def _freeze(window: _Window, best, details, calls, results) -> WindowLog:
    requests = sorted(
        (RequestInfo(best[key], details[key][0], details[key][1], details[key][2]) for key in window.keys),
        key=lambda info: info.order,
    )
    tool_calls = []
    for tool_id in window.call_ids:
        call, result = calls[tool_id], results.get(tool_id)
        tool_calls.append(
            ToolCallInfo(
                tool_id,
                call["name"],
                call["time"],
                result["time"] if result else None,
                bool(result and result["error"]),
                call["read_path"],
            )
        )
    return WindowLog(tuple(requests), tuple(tool_calls), window.first, window.last, window.human)
