"""Mutation testing: how many planted bugs does each run's own test suite catch?

Usage: python mutate.py <suite_name> <test_file> [<test_file> ...]
Runs the suite against the neutral reference with no bug (tests that fail there are
excluded as implementation-specific), then once per planted bug. Prints JSON.
"""
import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
REF = HERE / "ref"
PY = sys.executable
sys.path.insert(0, str(REF))
from main import MUTANTS  # noqa: E402

name, files = sys.argv[1], sys.argv[2:]


def run(mutant, deselect=()):
    with tempfile.TemporaryDirectory() as tmp:
        report = Path(tmp) / "r.xml"
        env = dict(os.environ, MUTANT=mutant, PYTHONPATH=str(REF), PYTHONDONTWRITEBYTECODE="1")
        args = [PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={report}", *files]
        for d in deselect:
            args += ["--deselect", d]
        subprocess.run(args, cwd=REF, env=env, capture_output=True, text=True, timeout=600)
        failed, total = [], 0
        for case in ET.parse(report).getroot().iter("testcase"):
            total += 1
            if case.find("failure") is not None or case.find("error") is not None:
                failed.append(f"{case.get('file') or ''}::{case.get('name')}")
        return total, failed


def nodeid(case):
    return case


total, base_fail = run("")
names = [f.split("::")[-1] for f in base_fail]
deselect = [f"{p}::{n}" for p in files for n in names]
killed = {}
for m in MUTANTS:
    t, failed = run(m, deselect)
    killed[m] = len(failed) > 0
print(json.dumps({"suite": name, "tests": total, "excluded_on_reference": names, "killed": killed,
                  "score": sum(killed.values()), "of": len(MUTANTS)}))
