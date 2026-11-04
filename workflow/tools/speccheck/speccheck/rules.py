"""Walk the rule registry over one spec folder and return findings."""

import re
from dataclasses import dataclass, field
from pathlib import Path

from .parse import (
    Section,
    find_section,
    find_tables,
    labelled_entries,
    list_item_text,
    numbered,
    outside_fences,
    placeholders,
    sections,
    tables,
)
from .registry import (
    OPTIONAL_SECTIONS,
    RULES,
    UI_PLAN_SECTION,
    UI_SPEC_SECTION,
    UI_WHERE,
    Rule,
)
from .waivers import Waiver

FILES = ("spec.md", "plan.md", "tasks.md")
ROLES = ("developer", "test-designer", "verifier", "spec-writer", "orchestrator", "human", "session", "user")
WHOLE_FILE = "(file)"
MAX_LABEL = 80

_ROLE = re.compile(r"\b(?:" + "|".join(ROLES) + r")\b", re.IGNORECASE)
_NO_SCREEN = re.compile(
    r"^\s*(?:(?:[-*+]|\d+\.)\s+)?(?:\*\*)?no screen(?:\*\*)?\s*:\s*(?:\*\*)?(.*)$", re.IGNORECASE
)
_AC_ITEM = re.compile(r"^\s*[-*+]\s+\[ \]\s+AC")


@dataclass(frozen=True)
class Finding:
    spec_id: str
    file: str
    heading: str
    code: str
    message: str
    line: int = 0


@dataclass
class _Context:
    spec_id: str
    texts: dict
    secs: dict
    no_screen: tuple | None  # (line, reason) of the first "No screen" line
    screen: bool  # screen rules apply
    entries: dict = field(default_factory=dict)  # labelled entries per (file, section)

    def section(self, file: str, name: str) -> Section | None:
        return find_section(self.secs[file], name) if self.texts[file] is not None else None

    def labelled(self, file: str, name: str) -> list:
        if (file, name) not in self.entries:
            section = self.section(file, name)
            self.entries[file, name] = labelled_entries(section) if section else []
        return self.entries[file, name]

    def finding(self, file, heading, code, message, line=0) -> Finding:
        return Finding(self.spec_id, file, heading, code, message, line)


def _read(path: Path) -> str | None:
    try:
        return path.read_bytes().decode("utf-8-sig", errors="replace") if path.is_file() else None
    except OSError:
        return None


def _find_no_screen(text: str | None) -> tuple | None:
    for n, line in outside_fences(numbered(text or "")):
        match = _NO_SCREEN.match(line)
        if match:
            return n, match[1].strip()
    return None


def _build_context(path: Path) -> _Context:
    texts = {name: _read(path / name) for name in FILES}
    secs = {name: sections(text or "") for name, text in texts.items()}
    no_screen = _find_no_screen(texts["spec.md"])
    declared = bool(no_screen and no_screen[1] and not placeholders(no_screen[1]))
    return _Context(path.name, texts, secs, no_screen, not declared)


def _has_text(section: Section) -> bool:
    return any(text.strip() for _, text in section.lines)


def _file(ctx, rule):
    if ctx.texts[rule.file] is None:
        return [ctx.finding(rule.file, WHOLE_FILE, rule.id, f"{rule.file} not found")]
    return []


def _no_screen_reason(ctx, rule):
    if ctx.no_screen and not ctx.no_screen[1]:
        n = ctx.no_screen[0]
        return [ctx.finding(rule.file, WHOLE_FILE, "NO_SCREEN_REASON_EMPTY", f'line {n}: "No screen" has no reason after the colon', n)]
    return []


def _section(ctx, rule):
    if ctx.texts[rule.file] is None:
        return []
    section = ctx.section(rule.file, rule.where)
    if section is None:
        return [ctx.finding(rule.file, WHOLE_FILE, "SECTION_MISSING", f'no "{rule.where}" section')]
    if not _has_text(section):
        return [ctx.finding(rule.file, section.heading, "SECTION_EMPTY", "section has no text", section.line)]
    return []


def _ac_item(ctx, rule):
    section = ctx.section(rule.file, rule.where)
    if section is None or any(_AC_ITEM.match(t) for _, t in outside_fences(section.lines)):
        return []
    message = 'section has no "- [ ] AC" checklist item'
    return [ctx.finding(rule.file, section.heading, rule.id, message, section.line)]


def _task_role(ctx, rule):
    if ctx.texts["tasks.md"] is None:
        return []
    lines = outside_fences(numbered(ctx.texts["tasks.md"]))
    items = [list_item_text(text) for _, text in lines]
    rows = [" ".join(cells) for table in find_tables(lines) for _, cells in table.rows]
    if any(_ROLE.search(text) for text in [*rows, *(i for i in items if i)]):
        return []
    message = f"no table row or list item names an owner role (accepted: {', '.join(ROLES)})"
    return [ctx.finding(rule.file, WHOLE_FILE, rule.id, message)]


def _ui_section_missing(ctx, rule):
    if ctx.texts["spec.md"] is None or ctx.section("spec.md", UI_SPEC_SECTION):
        return []
    message = f'no "{UI_SPEC_SECTION}" section and no "No screen: reason" line'
    return [ctx.finding("spec.md", WHOLE_FILE, rule.id, message)]


def _ui_table_empty(ctx, rule):
    section = ctx.section("spec.md", UI_SPEC_SECTION)
    if section and not any(t.rows for t in tables(section)):
        return [ctx.finding("spec.md", section.heading, rule.id, "section has no table data rows", section.line)]
    return []


def _ui_cell_empty(ctx, rule):
    section = ctx.section("spec.md", UI_SPEC_SECTION)
    found = []
    for table in tables(section) if section else []:
        for number, cells in table.rows:
            for i, header in enumerate(table.header):
                if i >= len(cells) or not cells[i]:
                    message = f'row {number}, column "{header or i + 1}" is empty'
                    found.append(ctx.finding("spec.md", section.heading, rule.id, message, section.line))
    return found


def _ui_contract_missing(ctx, rule):
    if ctx.texts["plan.md"] is None or ctx.section("plan.md", UI_PLAN_SECTION):
        return []
    return [ctx.finding("plan.md", WHOLE_FILE, rule.id, f'no "{UI_PLAN_SECTION}" section')]


def _ui_contract_empty(ctx, rule):
    section = ctx.section("plan.md", UI_PLAN_SECTION)
    if section and not _has_text(section):
        return [ctx.finding("plan.md", section.heading, rule.id, "section has no text", section.line)]
    return []


def _scanned_sections(ctx):
    names = [(r.file, r.where) for r in RULES if r.id.startswith("SECTION ")]
    names += OPTIONAL_SECTIONS
    if ctx.screen:
        names += [("spec.md", UI_SPEC_SECTION), ("plan.md", UI_PLAN_SECTION)]
    return names


def _placeholder(ctx, rule):
    found, seen = [], set()

    def scan(file, heading, number, text, allow_todo=False):
        hits = placeholders(text, allow_todo)
        if hits and (file, number) not in seen:
            seen.add((file, number))
            message = f'line {number}: placeholder text "{hits[0]}"'
            found.append(ctx.finding(file, heading, rule.id, message, number))

    if ctx.no_screen:
        scan("spec.md", WHOLE_FILE, ctx.no_screen[0], ctx.no_screen[1])
    for file, name in _scanned_sections(ctx):
        section = ctx.section(file, name)
        for number, text in outside_fences(section.lines) if section else []:
            scan(file, section.heading, number, text)
    for number, text in outside_fences(numbered(ctx.texts["tasks.md"] or "")):
        scan("tasks.md", WHOLE_FILE, number, text, allow_todo=True)
    for file in FILES:
        if ctx.secs[file]:
            first = ctx.secs[file][0]
            scan(file, WHOLE_FILE, first.line, first.heading, allow_todo=file == "tasks.md")
    return found


def _places(rule: Rule) -> list[tuple[str, str]]:
    if rule.where == UI_WHERE:
        return [("spec.md", UI_SPEC_SECTION), ("plan.md", UI_PLAN_SECTION)]
    return [(rule.file, rule.where)]


def _label_matches(rule: Rule, label: str) -> bool:
    lowered = label.lower()
    return len(label) <= MAX_LABEL and any(
        all(re.search(pattern, lowered) for pattern in group) for group in rule.groups
    )


def _words(pattern: str) -> str:
    return " or ".join(f'"{w}"' for w in pattern.lstrip("^").replace("[ -]", " ").split("|"))


def _group_text(group: tuple) -> str:
    words = [_words(pattern) for pattern in group]
    return words[0] if len(words) == 1 else f"{', '.join(words[:-1])} and {words[-1]}"


def _accepted(rule: Rule) -> str:
    groups = "; or ".join(_group_text(group) for group in rule.groups)
    return f'a label with {groups}, e.g. "{rule.example}"'


def _item(ctx, rule):
    places = _places(rule)
    if any(ctx.texts[file] is None for file, _ in places):
        return []
    found = [ctx.section(file, name) for file, name in places]
    entries = [e for file, name in places for e in ctx.labelled(file, name)]
    matching = [e for e in entries if _label_matches(rule, e.label)]
    if any(e.content for e in matching):
        return []
    file, home = places[-1][0], found[-1]
    heading, line = (home.heading, home.line) if home else (WHOLE_FILE, 0)
    if matching:
        return [ctx.finding(file, heading, "ITEM_EMPTY", f"item {rule.id} has a label but no content", line)]
    message = f"item {rule.id} missing; accepted labels: {_accepted(rule)}"
    return [ctx.finding(file, heading, "ITEM_MISSING", message, line)]


_BY_ID = {
    "NO_SCREEN": _no_screen_reason,
    "AC_ITEM_MISSING": _ac_item,
    "TASKS_NO_ROLE": _task_role,
    "UI_SECTION_MISSING": _ui_section_missing,
    "UI_TABLE_EMPTY": _ui_table_empty,
    "UI_TABLE_CELL_EMPTY": _ui_cell_empty,
    "UI_CONTRACT_MISSING": _ui_contract_missing,
    "UI_CONTRACT_EMPTY": _ui_contract_empty,
    "PLACEHOLDER": _placeholder,
}
_BY_KIND = {"file": _file, "section": _section, "item": _item}


def check_spec_dir(path: Path, waivers: dict[str, Waiver]) -> list[Finding]:
    """Findings for one spec folder (the spec id is the folder name), in report order."""
    waiver = waivers.get(path.name)
    if waiver and waiver.scope == "all":
        return []
    ctx = _build_context(path)
    found = []
    for order, rule in enumerate(RULES):
        if (rule.skip_no_screen and not ctx.screen) or (rule.skip_added_items and waiver):
            continue
        handler = _BY_ID.get(rule.id) or _BY_KIND[rule.kind]
        found.extend((f.file, f.line, order, f) for f in handler(ctx, rule))
    found.sort(key=lambda entry: entry[:3])
    return [entry[3] for entry in found]
