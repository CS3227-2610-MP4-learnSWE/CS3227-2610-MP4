"""Tests for the Phase 2 report parser (written before phase2.py)."""
import json

from phase2 import hint_for, parse_junit, render_markdown

XML = """<?xml version="1.0"?>
<testsuites><testsuite tests="6">
<testcase classname="tests.test_a" name="test_adm01_ok" time="0.1"/>
<testcase classname="tests.test_a" name="test_adm01_import">
  <failure message="ImportError: cannot import name x">Traceback
ImportError: cannot import name x
line3
line4
line5
line6</failure></testcase>
<testcase classname="tests.test_a" name="test_adm01_status">
  <failure message="assert 404 == 200">assert 404 == 200</failure></testcase>
<testcase classname="tests.test_a" name="test_adm01_logic">
  <failure message="assert 3 == 4">assert 3 == 4</failure></testcase>
<testcase classname="tests.test_a" name="test_adm01_skip"><skipped message="no db"/></testcase>
<testcase classname="tests.test_a" name="test_adm01_err"><error message="KeyError: 'k'">KeyError: 'k'</error></testcase>
</testsuite></testsuites>"""


def test_counts():
    r = parse_junit(XML)
    assert (r["passed"], r["failed"], r["skipped"], r["total"]) == (1, 4, 1, 6)


def test_failing_ids_and_excerpt_limited_to_five_lines():
    r = parse_junit(XML)
    ids = [f["id"] for f in r["failures"]]
    assert "tests.test_a::test_adm01_import" in ids
    imp = next(f for f in r["failures"] if f["id"].endswith("import"))
    assert len(imp["excerpt"].splitlines()) <= 5


def test_hints():
    assert "contract" in hint_for("ImportError: x")
    assert "contract" in hint_for("KeyError: 'k'")
    assert "contract" in hint_for("assert 404 == 200")
    assert "contract" in hint_for("AttributeError: no attr")
    assert "logic" in hint_for("assert 3 == 4")


def test_markdown_labels_hints_as_heuristic_and_json_roundtrips():
    r = parse_junit(XML)
    md = render_markdown(r)
    assert "heuristic" in md.lower() and "test_adm01_logic" in md
    json.dumps(r)
