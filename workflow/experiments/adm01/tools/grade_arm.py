"""Q1 grading: run the frozen ADM-01 suite against an arm worktree.

Needs TEA01_TEST_DATABASE_URL (a throwaway Postgres); all frozen tests skip without it,
and skips never count as a pass.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

_COUNT = re.compile(r"(\d+) (passed|failed|error|errors|skipped)\b")
_KEYS = {"passed": "passed", "failed": "failed", "error": "errors", "errors": "errors", "skipped": "skipped"}


def parse_summary(text):
    counts = {"passed": 0, "failed": 0, "errors": 0, "skipped": 0}
    found = False
    for n, word in _COUNT.findall(text):
        counts[_KEYS[word]] += int(n)
        found = True
    return counts if found else None


def q1_pass(result, expected):
    return (
        result is not None
        and result["passed"] == expected
        and result["failed"] == 0
        and result["errors"] == 0
        and result["skipped"] == 0
    )


def install_frozen(src, tests_dir, files):
    for name in files:
        shutil.copyfile(Path(src) / name, Path(tests_dir) / name)


def _pytest(backend_dir, files):
    proc = subprocess.run(
        ["uv", "run", "pytest", "-q", *files],
        cwd=backend_dir, capture_output=True, text=True,
    )
    return proc.stdout + proc.stderr


def grade(arm_dir, frozen_dir, files, expected, runner=_pytest):
    if not os.environ.get("TEA01_TEST_DATABASE_URL"):
        return {"status": "blocked", "reason": "TEA01_TEST_DATABASE_URL is not set"}
    backend = Path(arm_dir) / "src" / "backend"
    install_frozen(frozen_dir, backend / "tests", files)
    summary = parse_summary(runner(backend, [f"tests/{f}" for f in files]))
    return {"status": "done", "q1": q1_pass(summary, expected), "summary": summary}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--arm-dir", required=True)
    p.add_argument("--frozen-dir", required=True)
    p.add_argument("--files", nargs="+", required=True)
    p.add_argument("--expected", type=int, required=True)
    args = p.parse_args(argv)
    result = grade(args.arm_dir, args.frozen_dir, args.files, args.expected)
    print(json.dumps(result, indent=2))
    return 0 if result.get("q1") else 1


if __name__ == "__main__":
    sys.exit(main())
