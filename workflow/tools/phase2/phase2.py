"""Phase 2 (verify) without an agent: merge the run branch into the test
worktree, run pytest, write a compact markdown + JSON report.

Usage: python phase2.py RUN_BRANCH TEST_WORKTREE PYTHON [--out DIR]
Never edits tests. Exit code 0 when all tests pass, 1 when some fail, 2 on
merge failure or a missing JUnit file.
"""
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

CONTRACT_RE = re.compile(r"ImportError|ModuleNotFoundError|AttributeError|KeyError|\b40[45]\b")


def hint_for(text):
    if CONTRACT_RE.search(text):
        return "possible contract mismatch (heuristic)"
    return "possible logic bug (heuristic)"


def parse_junit(xml_text):
    passed = failed = skipped = 0
    failures = []
    for c in ET.fromstring(xml_text).iter("testcase"):
        bad = c.find("failure")
        if bad is None:
            bad = c.find("error")
        if bad is not None:
            failed += 1
            body = (bad.text or bad.get("message") or "").strip()
            failures.append({
                "id": f"{c.get('classname')}::{c.get('name')}",
                "excerpt": "\n".join(body.splitlines()[:5]),
                "hint": hint_for(body + " " + (bad.get("message") or "")),
            })
        elif c.find("skipped") is not None:
            skipped += 1
        else:
            passed += 1
    return {"total": passed + failed + skipped, "passed": passed, "failed": failed,
            "skipped": skipped, "failures": failures}


def render_markdown(r):
    out = ["# Phase 2 report", "",
           f"total {r['total']}, passed {r['passed']}, failed {r['failed']}, skipped {r['skipped']}", ""]
    if r["failures"]:
        out += ["Hints are heuristic only (keyword match), not a diagnosis.", ""]
    for f in r["failures"]:
        out += [f"## {f['id']}", f"Hint (heuristic): {f['hint']}", "```", f["excerpt"], "```", ""]
    return "\n".join(out)


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    branch, wt, python = argv[0], Path(argv[1]), argv[2]
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else wt
    merge = run(["git", "merge", "--no-edit", branch], wt)
    if merge.returncode != 0:
        run(["git", "merge", "--abort"], wt)
        (out / "phase2-report.md").write_text("# Phase 2 report\n\nMERGE FAILED\n\n" + merge.stdout + merge.stderr)
        return 2
    xml = out / "phase2-junit.xml"
    run([python, "-m", "pytest", "-q", f"--junitxml={xml}", "-p", "no:cacheprovider"], wt / "src" / "backend")
    if not xml.exists():
        (out / "phase2-report.md").write_text("# Phase 2 report\n\nNO JUNIT FILE (pytest did not run)\n")
        return 2
    r = parse_junit(xml.read_text(encoding="utf-8"))
    (out / "phase2-report.md").write_text(render_markdown(r), encoding="utf-8")
    (out / "phase2-report.json").write_text(json.dumps(r, indent=2), encoding="utf-8")
    print(f"phase2: {r['passed']} passed, {r['failed']} failed, {r['skipped']} skipped")
    return 0 if r["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
