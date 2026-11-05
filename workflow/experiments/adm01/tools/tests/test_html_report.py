import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import html_report


def test_escapes_values():
    out = html_report.render({"A": {"cost_usd": 1.0, "note": "<script>x</script>"}}, {})
    assert "<script>x" not in out
    assert "&lt;script&gt;" in out


def test_not_run_and_unavailable_shown():
    out = html_report.render({"A": {"cost_usd": None}, "H1": None}, {"H1": "not run"})
    assert "not run" in out
    assert "unavailable" in out


def test_states_estimate_disclaimer():
    assert "list-price estimates, not billed" in html_report.render({}, {})


def test_is_complete_document():
    out = html_report.render({}, {})
    assert out.startswith("<!doctype html>") and "</html>" in out
