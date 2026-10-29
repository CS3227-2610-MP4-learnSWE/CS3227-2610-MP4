"""Grade one finished run: apply the hidden grader suite to a run branch.

Usage (from the repo root):
    python workflow/experiments/stu02/grade_run.py exp/stu02-A --label A

Checks the run branch out into a temporary worktree, copies the grader tests in
from the grader branch, runs them plus the run's own tests, and writes
workflow/experiments/results/stu02-<label>-grade.json. The run branch itself is
never modified.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
GRADER_BRANCH = "exp/stu02-grader"
GRADER_FILE = "src/backend/tests/grader/test_stu02_grader.py"
RESULTS = REPO / "workflow" / "experiments" / "results"


def git(*args: str, cwd: Path = REPO) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def pytest_command() -> list[str]:
    """Run pytest in the run's own locked environment, so a dependency the run added is installed."""
    if shutil.which("uv"):
        return ["uv", "run", "--frozen", "--quiet", "python", "-m", "pytest"]
    print("warning: uv not found; using this Python, which may lack the run's dependencies", file=sys.stderr)
    return [sys.executable, "-m", "pytest"]


def run_pytest(backend: Path, targets: list[str], extra: list[str]) -> dict:
    """Run pytest and return passed, failed, total and the names of failures."""
    with tempfile.TemporaryDirectory() as tmp:
        report = Path(tmp) / "report.xml"
        subprocess.run(
            [*pytest_command(), *targets, *extra, "-q", f"--junitxml={report}"],
            cwd=backend,
            capture_output=True,
            text=True,
        )
        return parse_junit(report) if report.is_file() else {"passed": 0, "failed": 0, "total": 0, "failures": [], "error": "no report"}


def parse_junit(report: Path) -> dict:
    cases = ET.parse(report).getroot().iter("testcase")
    failures, total = [], 0
    for case in cases:
        total += 1
        if case.find("failure") is not None or case.find("error") is not None:
            failures.append(case.get("name", ""))
    return {"passed": total - len(failures), "failed": len(failures), "total": total, "failures": failures}


def grade(branch: str, label: str) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        tree = Path(tmp) / "run"
        git("worktree", "add", "--detach", str(tree), branch)
        try:
            backend = tree / "src" / "backend"
            own = run_pytest(backend, ["tests"], ["--ignore=tests/grader"])
            grader_path = tree / GRADER_FILE
            grader_path.parent.mkdir(parents=True, exist_ok=True)
            grader_path.write_text(git("show", f"{GRADER_BRANCH}:{GRADER_FILE}"), encoding="utf-8")
            graded = run_pytest(backend, ["tests/grader"], [])
        finally:
            git("worktree", "remove", "--force", str(tree))
    return {"label": label, "branch": branch, "commit": git("rev-parse", "--short", branch).strip(), "grader": graded, "own_tests": own}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("branch")
    parser.add_argument("--label", required=True)
    args = parser.parse_args(argv)
    result = grade(args.branch, args.label)
    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / f"stu02-{args.label}-grade.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    g, o = result["grader"], result["own_tests"]
    print(f"{args.label}: grader {g['passed']}/{g['total']} passed; own tests {o['passed']}/{o['total']} passed -> {out}")
    for name in g["failures"]:
        print(f"  grader failure: {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
