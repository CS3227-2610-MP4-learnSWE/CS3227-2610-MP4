"""The rule table. Data only: the checker walks RULES and `--list-rules` prints it."""

from dataclasses import dataclass

UI_SPEC_SECTION = "UI states and copy"
UI_PLAN_SECTION = "UI contract"
SECURITY_SECTION = "Security and AI safeguards"
UI_WHERE = "UI"

# Sections that are checked for placeholders only when present.
OPTIONAL_SECTIONS = (("plan.md", "Decisions"),)


@dataclass(frozen=True)
class Rule:
    id: str
    tier: int
    file: str
    kind: str
    where: str
    groups: tuple
    skip_no_screen: bool
    skip_added_items: bool
    source: str
    example: str = ""


def _rule(rule_id, tier, file, kind, where, source, no_screen=False, added=False):
    return Rule(rule_id, tier, file, kind, where, (), no_screen, added, source)


def _section(file, name, source):
    return _rule(f"SECTION {name}", 1, file, "section", name, f"{source} (SECTION_MISSING, SECTION_EMPTY)")


def _item(rule_id, where, groups, example, source, no_screen):
    file = "spec.md or plan.md" if where == UI_WHERE else "spec.md"
    return Rule(rule_id, 2, file, "item", where, groups, no_screen, True, f"{source} (ITEM_MISSING, ITEM_EMPTY)", example)


_SPEC = "template spec.md"
_PLAN = "template plan.md"

RULES: tuple[Rule, ...] = (
    _rule("SPEC_MISSING", 1, "spec.md", "file", "file", "spec-writer: output spec.md"),
    _rule("PLAN_MISSING", 1, "plan.md", "file", "file", "spec-writer: output plan.md"),
    _rule("TASKS_MISSING", 1, "tasks.md", "file", "file", "spec-writer: output tasks.md"),
    _rule("NO_SCREEN", 1, "spec.md", "section", "No screen line", "design decision (NO_SCREEN_REASON_EMPTY)"),
    _section("spec.md", "Goal", _SPEC),
    _section("spec.md", "Behaviour", _SPEC),
    _section("spec.md", "Acceptance criteria", _SPEC),
    _rule("AC_ITEM_MISSING", 1, "spec.md", "ac-item", "Acceptance criteria", _SPEC),
    _section("spec.md", "Out of scope", _SPEC),
    _section("spec.md", SECURITY_SECTION, _SPEC),
    _section("spec.md", "Open questions", f"{_SPEC}; role: flag ambiguities"),
    _section("plan.md", "Data model", _PLAN),
    _section("plan.md", "API endpoints", _PLAN),
    _section("plan.md", "Components and modules", _PLAN),
    _section("plan.md", "Test plan", _PLAN),
    _rule("TASKS_NO_ROLE", 1, "tasks.md", "task-role", "table rows or list items", "role: tasks tagged with owning role"),
    _rule("UI_SECTION_MISSING", 2, "spec.md", "table", UI_SPEC_SECTION, "role: UI states table", no_screen=True),
    _rule("UI_TABLE_EMPTY", 2, "spec.md", "table", UI_SPEC_SECTION, "role: UI states table", no_screen=True),
    _rule("UI_TABLE_CELL_EMPTY", 2, "spec.md", "table", UI_SPEC_SECTION, "role: UI states table", no_screen=True),
    _rule("UI_CONTRACT_MISSING", 2, "plan.md", "section", UI_PLAN_SECTION, "role: plan UI contract", no_screen=True),
    _rule("UI_CONTRACT_EMPTY", 2, "plan.md", "section", UI_PLAN_SECTION, "role: plan UI contract", no_screen=True),
    _rule("PLACEHOLDER", 1, "all", "section", "Tier 1 sections, screen sections, first heading line", "role: a state not written down is a guess"),
    _item("REQUESTS", UI_WHERE, (("requests", "per", "load|retry"),), "Requests per load and per retry", "requests sent per load and per retry", True),
    _item("WRONG_ROLE", UI_WHERE, (("wrong[ -]role",),), "Wrong role", "what a wrong-role user sees", True),
    _item("HISTORY", UI_WHERE, (("push", "replace"), ("^link history",)), "Link history: push or replace", "push versus replace for each link", True),
    _item("REFRESH", UI_WHERE, (("refresh",),), "Refresh", "what a user sees on refresh", True),
    _item("BACK_FORWARD", UI_WHERE, (("back", "forward"),), "Back and Forward", "Back and Forward", True),
    _item("EXPIRED_SESSION", UI_WHERE, (("expired session",), ("logout",)), "Expired session or logout", "after logout or an expired session", True),
    _item("BACKEND_DOWN", UI_WHERE, (("backend down",),), "Backend down", "with the backend down", True),
    _item("LONGEST_WAIT", UI_WHERE, (("longest wait",), ("timeout",)), "Longest wait before an error", "the longest time any screen waits before showing an error", True),
    _item("NO_GENERIC_FAILURE", UI_WHERE, (("generic",),), "No generic failure message", "no failure hides behind a generic message", True),
    _item("CONCURRENT_REQUESTS", SECURITY_SECTION, (("concurrent",), ("same time",)), "Concurrent requests (same time)", "two requests for the same record at the same time", False),
    _item("NORMALISATION", SECURITY_SECTION, (("normali[sz]",),), "Normalisation", "how identifiers and inputs are normalised", False),
)
