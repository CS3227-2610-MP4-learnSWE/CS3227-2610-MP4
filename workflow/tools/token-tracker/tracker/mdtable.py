"""Markdown table helpers shared by the run reports."""

from __future__ import annotations

from collections.abc import Sequence


def escape_cell(text: str) -> str:
    """Escape backslashes and pipes, and turn line breaks into `<br>`."""
    return str(text).replace("\\", "\\\\").replace("|", "\\|").replace("\r\n", "\n").replace("\n", "<br>")


def table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    """A pipe table; cells are used as given (escape them first)."""
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)
