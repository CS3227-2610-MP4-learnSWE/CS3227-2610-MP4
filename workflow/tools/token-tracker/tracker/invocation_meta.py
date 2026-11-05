"""The optional metadata sidecar: a CSV keyed by invocation ID that adds human-supplied context to output rows."""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Sequence
from pathlib import Path

from .errors import TrackerError

META_COLUMNS = [
    "invocation_id",
    "role_label",
    "arm",
    "phase",
    "revision_round",
    "trigger",
    "start_commit",
    "end_commit",
    "agent_definition_hash",
]
TRIGGERS = ("first", "retry", "revision", "resume")
_ROUND = re.compile(r"[0-9]+")


def read_metadata(path: Path | None, known_ids: Sequence[str]) -> dict[str, dict[str, str]]:
    """Validated sidecar cells by invocation ID (trimmed); an empty dict when no file is given."""
    if path is None:
        return {}
    label = f'--meta file "{path}"'
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        raise TrackerError(f"{label} cannot be read: not valid UTF-8 text") from None
    except OSError as exc:
        raise TrackerError(f"{label} cannot be read: {exc.strerror or exc}") from None

    reader = csv.reader(io.StringIO(text, newline=""))
    header = next(reader, [])
    if header != META_COLUMNS:
        raise TrackerError(
            f'{label} line 1: header is "{", ".join(header)}" but must be exactly: {", ".join(META_COLUMNS)}'
        )
    result: dict[str, dict[str, str]] = {}
    lines: dict[str, int] = {}
    for row in reader:
        line = reader.line_num
        if not row:
            continue
        if len(row) != len(META_COLUMNS):
            raise TrackerError(f"{label} line {line}: expected {len(META_COLUMNS)} fields but found {len(row)}")
        invocation_id = row[0]
        if invocation_id not in known_ids:
            raise TrackerError(
                f'{label} line {line}: invocation ID "{invocation_id}" is not in this run; '
                f"the run's IDs are: {', '.join(known_ids)}"
            )
        if invocation_id in lines:
            raise TrackerError(f'{label} line {line}: invocation ID "{invocation_id}" already appears on line {lines[invocation_id]}')
        cells = dict(zip(META_COLUMNS[1:], (cell.strip() for cell in row[1:])))
        if cells["trigger"] and cells["trigger"] not in TRIGGERS:
            raise TrackerError(
                f'{label} line {line}: trigger "{cells["trigger"]}" is not allowed; use one of: {", ".join(TRIGGERS)}'
            )
        if cells["revision_round"] and not _ROUND.fullmatch(cells["revision_round"]):
            raise TrackerError(f'{label} line {line}: revision_round "{cells["revision_round"]}" is not a non-negative integer')
        lines[invocation_id] = line
        result[invocation_id] = cells
    return result


def apply_metadata(rows: list[dict[str, object]], meta: dict[str, dict[str, str]]) -> None:
    """Set `role_label` and the seven metadata columns on each invocation row (None when missing or empty)."""
    for row in rows:
        cells = meta.get(row["invocation_id"], {})
        for column in META_COLUMNS[1:]:
            row[column] = cells.get(column) or None
