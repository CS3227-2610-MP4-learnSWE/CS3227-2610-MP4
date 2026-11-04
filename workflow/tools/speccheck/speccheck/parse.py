"""Markdown to sections, tables, labelled entries and placeholder text. No file access."""

import re
from dataclasses import dataclass

_HEADING = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.*)$")
_LIST_ITEM = re.compile(r"^(\s*)(?:[-*+]|\d+\.)\s+(.*)$")
_BOLD = re.compile(r"^\*\*(.+?)\*\*(.*)$")
_SEPARATOR_CELL = re.compile(r"^:?-+:?$")
_CELL_SPLIT = re.compile(r"(?<!\\)\|")
_CODE_SPAN = re.compile(r"`[^`]*`")
_PLACEHOLDER = re.compile(
    r"\b(?:TBD|TODO|TBC|FIXME|XXX)\b|\?\?\?|<(?!br\s*/?>)[^<>\n]+>", re.IGNORECASE
)
_TODO = re.compile(r"todo", re.IGNORECASE)
_TRAILING = ".:;,!? \t"
_MAX_CONTENT_LINES = 20
_CONTENT_BUDGET = 100_000

Lines = list[tuple[int, str]]


@dataclass(frozen=True)
class Section:
    heading: str
    level: int
    line: int
    lines: Lines


@dataclass(frozen=True)
class Table:
    header: list[str]
    rows: list[tuple[int, list[str]]]


@dataclass(frozen=True)
class Entry:
    label: str
    content: str
    line: int


def _heading(text: str) -> tuple[int, str] | None:
    """(level, text) of an ATX heading line, or None."""
    match = _HEADING.match(text)
    title = match[2].strip() if match else ""
    return (len(match[1]), title) if title else None


def numbered(text: str) -> Lines:
    """Split text into (1-based line number, line) pairs."""
    return [(n, line.rstrip("\r")) for n, line in enumerate(text.split("\n"), 1)]


def _is_fence(text: str) -> bool:
    stripped = text.lstrip()
    return stripped.startswith("```") or stripped.startswith("~~~")


def outside_fences(lines: Lines) -> Lines:
    """Drop fenced code blocks and their fence lines."""
    kept: Lines = []
    inside = False
    for n, text in lines:
        if _is_fence(text):
            inside = not inside
        elif not inside:
            kept.append((n, text))
    return kept


def heading_key(text: str) -> str:
    cleaned = text.strip().replace("**", "").replace("`", "").lower()
    return cleaned.rstrip(_TRAILING).strip()


def sections(text: str) -> list[Section]:
    """Sections in document order; each includes the lines of its sub-sections."""
    open_entries: list[tuple[str, int, int, Lines]] = []
    all_entries: list[tuple[str, int, int, Lines]] = []
    inside = False
    for n, line in numbered(text):
        if _is_fence(line):
            inside = not inside
        match = None if inside else _heading(line)
        if match:
            level = match[0]
            while open_entries and open_entries[-1][1] >= level:
                open_entries.pop()
            for parent in open_entries:
                parent[3].append((n, line))
            entry = (match[1], level, n, [])
            open_entries.append(entry)
            all_entries.append(entry)
        else:
            for parent in open_entries:
                parent[3].append((n, line))
    return [Section(*entry) for entry in all_entries]


def find_section(secs: list[Section], name: str) -> Section | None:
    wanted = heading_key(name)
    return next((s for s in secs if heading_key(s.heading) == wanted), None)


def split_cells(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|") and not stripped.endswith("\\|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in _CELL_SPLIT.split(stripped)]


def _is_pipe(text: str) -> bool:
    return text.lstrip().startswith("|")


def _is_separator(text: str) -> bool:
    return all(_SEPARATOR_CELL.match(cell) for cell in split_cells(text))


def _pipe_runs(lines: Lines) -> list[Lines]:
    runs: list[Lines] = []
    run: Lines = []
    for item in lines:
        if _is_pipe(item[1]) and (not run or item[0] == run[-1][0] + 1):
            run.append(item)
            continue
        runs.append(run)
        run = [item] if _is_pipe(item[1]) else []
    runs.append(run)
    return [r for r in runs if len(r) >= 2 and _is_separator(r[1][1])]


def _raw_tables(lines: Lines) -> list[tuple[list[str], list[tuple[int, list[str]]]]]:
    """Tables as (header, [(line number, cells)]) for the given lines."""
    return [
        (split_cells(run[0][1]), [(n, split_cells(text)) for n, text in run[2:]])
        for run in _pipe_runs(lines)
    ]


def find_tables(lines: Lines) -> list[Table]:
    return [
        Table(header, [(i, cells) for i, (_, cells) in enumerate(rows, 1)])
        for header, rows in _raw_tables(lines)
    ]


def tables(section: Section) -> list[Table]:
    return find_tables(outside_fences(section.lines))


def list_item_text(line: str) -> str | None:
    """Text after the list marker, or None when the line is not a list item."""
    match = _LIST_ITEM.match(line)
    return match[2] if match else None


def placeholders(line: str, allow_todo: bool = False) -> list[str]:
    """Placeholder text found in a line, ignoring backtick code spans."""
    found = _PLACEHOLDER.findall(_CODE_SPAN.sub("", line))
    return [m for m in found if not (allow_todo and _TODO.fullmatch(m))]


def _clean_label(label: str) -> str:
    return label.replace("*", "").replace("`", "").strip().rstrip(_TRAILING).strip()


def _split_label(text: str) -> tuple[str, str]:
    bold = _BOLD.match(text) if text.startswith("**") else None
    if bold:
        label, _, inner_tail = bold[1].partition(":")
        outer_tail = bold[2].strip().lstrip(":").strip()
        return _clean_label(label), " ".join(p for p in (inner_tail.strip(), outer_tail) if p)
    label, _, tail = text.partition(":")
    return _clean_label(label), tail.strip()


def _continuation(lines: Lines, start: int, kind: str, indent: int, budget: list[int]) -> str:
    gathered: list[str] = []
    if kind != "list":
        while start < len(lines) and not lines[start][1].strip():
            start += 1
    for _, text in lines[start : start + _MAX_CONTENT_LINES]:
        stripped = text.strip()
        if not stripped or _heading(text) or budget[0] <= 0:
            break
        budget[0] -= 1
        if kind != "heading" and stripped.startswith("**"):
            break
        if kind == "list" and _LIST_ITEM.match(text) and len(text) - len(text.lstrip()) <= indent:
            break
        gathered.append(stripped)
    return " ".join(gathered)


def labelled_entries(section: Section) -> list[Entry]:
    """Labelled entries: list items, table rows, bold lines and sub-headings."""
    lines = outside_fences(section.lines)
    rows = {n: cells for _, table in _raw_tables(lines) for n, cells in table}
    entries: list[Entry] = []
    budget = [_CONTENT_BUDGET]
    for i, (n, text) in enumerate(lines):
        if n in rows:
            cells = rows[n]
            label, content = _clean_label(cells[0]), " ".join(c for c in cells[1:] if c)
            entries.append(Entry(label, content, n))
            continue
        heading, item = _heading(text), _LIST_ITEM.match(text)
        if heading:
            kind, body, indent = "heading", heading[1], 0
        elif item:
            kind, body, indent = "list", item[2], len(item[1])
        elif text.lstrip().startswith("**"):
            kind, body, indent = "bold", text.strip(), 0
        else:
            continue
        label, content = _split_label(body)
        if not content:
            content = _continuation(lines, i + 1, kind, indent, budget)
        if label:
            entries.append(Entry(label, content, n))
    return entries
