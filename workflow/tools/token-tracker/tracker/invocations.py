"""Rebuild invocations (orchestrator per session, one per subagent prompt) from Claude Code logs."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from .claude_logs import agent_type as logged_agent_type
from .errors import TrackerError
from .log_session import FileLog, WindowLog, find_session_files, read_file_log
from .model import UsageRow
from .pricing import cost_usd

ORCHESTRATOR = "orchestrator"
_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
_ID_UNSAFE = re.compile(r"[^A-Za-z0-9._-]")


@dataclass(frozen=True)
class InvocationRecord:
    invocation_id: str
    run_id: str
    role: str
    session_id: str
    agent_id: str  # "" for the orchestrator
    prompt_number: int | None  # 1-based for subagents, None for the orchestrator
    launched_by: str | None  # None on a subagent means no Agent call matched (rendered "unavailable")
    requested_agent_type: str | None  # same None rules as launched_by
    window: WindowLog
    rows: tuple[UsageRow, ...]  # priced, in request order


@dataclass(frozen=True)
class BuildResult:
    records: tuple[InvocationRecord, ...]  # in numbering and output order
    warnings: tuple[str, ...]


@dataclass
class _Draft:
    session_id: str
    agent_id: str
    prompt_number: int | None
    role: str
    window: WindowLog
    tool_use_id: str = ""

    @property
    def is_orchestrator(self) -> bool:
        return self.prompt_number is None


def validate_run_id(run_id: str) -> None:
    if not _RUN_ID.fullmatch(run_id):
        raise TrackerError(
            f'--run-id "{run_id}" is invalid: it must start with a letter or digit and contain only letters, '
            "digits, '.', '_' and '-'"
        )


def build_invocations(run_id: str, claude_dir: Path, session_ids: Sequence[str], prices: dict) -> BuildResult:
    """Validate the inputs in the documented order, then cut, name, number and link the invocations."""
    validate_run_id(run_id)
    _validate_sessions(session_ids)
    found = {}
    for session_id in session_ids:
        main, subagents = find_session_files(claude_dir, session_id)
        if main is None and not subagents:
            projects = Path(claude_dir) / "projects"
            raise TrackerError(
                f'no Claude Code logs found for session ID "{session_id}" under {projects}: expected {session_id}.jsonl '
                f"or {session_id}/subagents/agent-*.jsonl in a project folder (check the session ID and --claude-dir)"
            )
        found[session_id] = (main, subagents)

    drafts: list[_Draft] = []
    warnings: list[str] = []
    main_logs: dict[str, FileLog] = {}
    for session_id in session_ids:
        main, subagents = found[session_id]
        if main is not None:
            log = read_file_log(main, logged_agent_type(main), split_prompts=False)
            main_logs[session_id] = log
            drafts.append(_Draft(session_id, "", None, ORCHESTRATOR, log.windows[0]))
        for path in subagents:
            log = read_file_log(path, logged_agent_type(path), split_prompts=True)
            role = _role(log)
            if role is None:
                role = "unknown"
                warnings.append(
                    f"warning: agent {log.agent_id} in session {session_id}: no usable meta.json "
                    "(file missing, unreadable or without a text agentType); role set to unknown"
                )
            tool_use_id = log.meta.get("toolUseId") if log.meta else None
            for number, window in enumerate(log.windows, start=1):
                drafts.append(
                    _Draft(session_id, log.agent_id, number, role, window, tool_use_id if isinstance(tool_use_id, str) else "")
                )

    drafts.sort(key=_order_key)
    ids = _number(run_id, drafts)
    orchestrator_ids = {d.session_id: ids[i] for i, d in enumerate(drafts) if d.is_orchestrator}
    records = [_record(run_id, ids[i], draft, main_logs, orchestrator_ids, prices) for i, draft in enumerate(drafts)]
    return BuildResult(tuple(records), tuple(warnings))


def _validate_sessions(session_ids: Sequence[str]) -> None:
    for position, session_id in enumerate(session_ids, start=1):
        if not session_id:
            raise TrackerError(
                f"session ID argument {position} is empty: give a non-empty Claude Code session ID"
            )
    first_seen: dict[str, int] = {}
    for position, session_id in enumerate(session_ids, start=1):
        if session_id in first_seen:
            raise TrackerError(
                f'session ID "{session_id}" is given more than once (arguments {first_seen[session_id]} and {position}): '
                "list each session once"
            )
        first_seen[session_id] = position


def _role(log: FileLog) -> str | None:
    agent = log.meta.get("agentType") if log.meta else None
    return agent if isinstance(agent, str) and agent.strip() else None


def _order_key(draft: _Draft) -> tuple:
    start = draft.window.first_time
    return (start is None, start.timestamp() if start else 0.0, draft.session_id, draft.agent_id, draft.prompt_number or 0)


def _number(run_id: str, drafts: list[_Draft]) -> list[str]:
    counters: dict[str, int] = {}
    ids = []
    for draft in drafts:
        role = _ID_UNSAFE.sub("_", draft.role)
        counters[role] = counters.get(role, 0) + 1
        ids.append(f"{run_id}-{role}-{counters[role]:02d}")
    return ids


def _record(run_id, invocation_id, draft, main_logs, orchestrator_ids, prices) -> InvocationRecord:
    launched_by = requested = None
    main = main_logs.get(draft.session_id)
    if not draft.is_orchestrator and main is not None and draft.tool_use_id in main.agent_calls:
        launched_by = orchestrator_ids.get(draft.session_id)
        requested = main.agent_calls[draft.tool_use_id]
    rows = tuple(replace(info.row, cost_usd=cost_usd(info.row, prices)) for info in draft.window.requests)
    return InvocationRecord(
        invocation_id, run_id, draft.role, draft.session_id, draft.agent_id, draft.prompt_number,
        launched_by, requested, draft.window, rows,
    )
