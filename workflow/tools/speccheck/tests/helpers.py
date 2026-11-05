"""Builders for synthetic spec folders used by the speccheck tests.

`spec_text`, `plan_text` and `tasks_text` return a complete passing document;
each test then breaks one thing (omit a section, replace a body, edit the text).
"""

import contextlib
import io
import re
import tempfile
import unittest
from pathlib import Path

SPEC_ID = "ZZ-01"
OMIT = object()  # pass as spec/plan/tasks to leave that file out

# Item code -> label used when writing an item line (the part before the first colon).
ITEM_LABELS = {
    "REQUESTS": "Requests per load and per retry",
    "WRONG_ROLE": "Wrong role",
    "HISTORY": "Link history",
    "REFRESH": "Refresh",
    "BACK_FORWARD": "Back and Forward",
    "EXPIRED_SESSION": "Expired session or logout",
    "BACKEND_DOWN": "Backend down",
    "LONGEST_WAIT": "Longest wait before an error",
    "NO_GENERIC_FAILURE": "No generic failure message",
    "CONCURRENT_REQUESTS": "Concurrent requests (same time)",
    "NORMALISATION": "Normalisation",
}
UI_ITEMS = (
    "REQUESTS",
    "WRONG_ROLE",
    "HISTORY",
    "REFRESH",
    "BACK_FORWARD",
    "EXPIRED_SESSION",
    "BACKEND_DOWN",
    "LONGEST_WAIT",
    "NO_GENERIC_FAILURE",
)
SECURITY_ITEMS = ("CONCURRENT_REQUESTS", "NORMALISATION")
SPEC_REQUIRED = (
    "Goal",
    "Behaviour",
    "Acceptance criteria",
    "Out of scope",
    "Security and AI safeguards",
    "Open questions",
)
PLAN_REQUIRED = ("Data model", "API endpoints", "Components and modules", "Test plan")
ROLES = (
    "developer",
    "test-designer",
    "verifier",
    "spec-writer",
    "orchestrator",
    "human",
    "session",
    "user",
)
UI_HEADING = "UI states and copy"
CONTRACT_HEADING = "UI contract"
SECURITY_HEADING = "Security and AI safeguards"
UI_TABLE = "| State | Copy |\n|---|---|\n| Loading | Loading the page |\n| Error | Could not load the page |"


def item_line(code, content="covered as described", marker="-"):
    return f"{marker} {ITEM_LABELS[code]}: {content}"


def ui_body(codes=UI_ITEMS, intro="Items for every screen state."):
    return intro + "\n\n" + "\n".join(item_line(c) for c in codes)


def security_body(codes=SECURITY_ITEMS):
    lines = ["- Read-only tool, no network."]
    lines += [item_line(c, "not applicable: the tool stores no records") for c in codes]
    return "\n".join(lines)


def render(title, sections, omit=(), bodies=None):
    omit = {o.lower() for o in omit}
    bodies = {k.lower(): v for k, v in (bodies or {}).items()}
    lines = [f"# {title}", ""]
    for heading, body in sections:
        if heading.lower() in omit:
            continue
        lines += [f"## {heading}", bodies.get(heading.lower(), body), ""]
    return "\n".join(lines) + "\n"


def spec_text(screen=True, no_screen=None, omit=(), bodies=None, title="Spec: ZZ-01 Demo feature"):
    """Complete passing spec.md. `no_screen` is a full declaration line; screen=False uses a default one."""
    secs = [
        ("Goal", "Show a demo page to the learner."),
        ("Behaviour", "1. The page loads and shows the lesson."),
    ]
    if screen:
        secs.append((UI_HEADING, UI_TABLE))
    if no_screen is not None or not screen:
        secs.append(("Screens", no_screen if no_screen is not None else "No screen: command-line tool, output in plan"))
    secs += [
        ("Acceptance criteria", "- [ ] AC1: The page shows the lesson.\n- [ ] AC2: A failure shows a retry message."),
        ("Out of scope", "Editing lessons."),
        (SECURITY_HEADING, security_body()),
        ("Open questions", "None."),
    ]
    return render(title, secs, omit, bodies)


def plan_text(screen=True, omit=(), bodies=None, title="Plan: ZZ-01 Demo feature"):
    secs = [
        ("Data model", "No stored data: a static page."),
        ("API endpoints", "Not applicable: no HTTP endpoints."),
        ("Components and modules", "New: one page component."),
    ]
    if screen:
        secs.append((CONTRACT_HEADING, ui_body()))
    secs.append(("Test plan", "One test per acceptance criterion."))
    return render(title, secs, omit, bodies)


def tasks_text(row="| 1 | Build the page | developer | none | todo |", title="Tasks: ZZ-01 Demo feature"):
    return f"# {title}\n\n| # | Task | Owner | Depends on | Status |\n|---|---|---|---|---|\n{row}\n"


def write_spec(root, spec_id=SPEC_ID, spec=None, plan=None, tasks=None):
    """Write a spec folder under root; None means the passing default, OMIT leaves the file out."""
    folder = Path(root) / spec_id
    folder.mkdir(parents=True, exist_ok=True)
    defaults = {"spec.md": spec_text, "plan.md": plan_text, "tasks.md": tasks_text}
    for name, given in (("spec.md", spec), ("plan.md", plan), ("tasks.md", tasks)):
        if given is OMIT:
            continue
        content = defaults[name]() if given is None else given
        target = folder / name
        if isinstance(content, bytes):
            target.write_bytes(content)
        else:
            target.write_text(content, encoding="utf-8")
    return folder


def line_of(text, needle):
    """1-based number of the first line containing needle."""
    for number, line in enumerate(text.splitlines(), start=1):
        if needle in line:
            return number
    raise AssertionError(f"{needle!r} not in text")


def replace_once(text, old, new):
    assert old in text, f"{old!r} not found"
    return text.replace(old, new, 1)


def codes(findings):
    return [f.code for f in findings]


def with_code(findings, code):
    return [f for f in findings if f.code == code]


def run_main(argv):
    """Call speccheck.cli.main with captured output; returns (exit code, stdout, stderr)."""
    from speccheck import cli

    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = cli.main([str(a) for a in argv])
        except SystemExit as exc:  # tolerate an argument parser that exits itself
            code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
    return code, out.getvalue(), err.getvalue()


def format_finding(f):
    return f'FAIL {f.spec_id} {f.file}: section "{f.heading}": {f.message} [{f.code}]'


FAIL_RE = re.compile(r'^FAIL (\S+) (spec\.md|plan\.md|tasks\.md): section "(.*)": (.*) \[([A-Z_]+)\]$')
SUMMARY_RE = re.compile(r"^speccheck: (\d+) checked, (\d+) failed, (\d+) waived$")


class SpecCase(unittest.TestCase):
    """Temp dir with a `specs` folder; helpers to write specs, waivers and run the checker."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.specs = self.root / "specs"
        self.specs.mkdir()

    def write(self, spec_id=SPEC_ID, spec=None, plan=None, tasks=None):
        return write_spec(self.specs, spec_id, spec, plan, tasks)

    def check(self, spec=None, plan=None, tasks=None, waivers=None, spec_id=SPEC_ID):
        from speccheck.rules import check_spec_dir

        folder = self.write(spec_id, spec, plan, tasks)
        return check_spec_dir(folder, waivers or {})

    def waiver_file(self, text, name="waivers.txt"):
        path = self.root / name
        path.write_text(text, encoding="utf-8")
        return path

    def waivers(self, text):
        from speccheck.waivers import load_waivers

        return load_waivers(self.waiver_file(text))

    def cli(self, *argv):
        return run_main(argv)
