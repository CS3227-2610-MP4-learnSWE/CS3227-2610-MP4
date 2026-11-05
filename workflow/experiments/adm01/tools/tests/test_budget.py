import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import budget


def test_cap_for_a_is_fixed():
    assert budget.cap_for("A", {}) == 15


def test_cap_later_arm_is_one_and_half_times_a():
    assert budget.cap_for("H3", {"A": 6.0}) == 9.0


def test_cap_never_above_15():
    assert budget.cap_for("H1", {"A": 12.0}) == 15


def test_cap_unknown_until_a_finished():
    assert budget.cap_for("H2", {}) is None


def test_status_ok_capped_unknown():
    assert budget.status("A", 14.99, {}) == "ok"
    assert budget.status("A", 15.01, {}) == "capped"
    assert budget.status("H3", 1.0, {}) == "unknown"
    assert budget.status("H3", 9.5, {"A": 6.0}) == "capped"


def test_cost_exactly_at_cap_is_ok():
    assert budget.status("A", 15, {}) == "ok"


def test_headroom_needed_is_one_and_half_a():
    assert budget.headroom_needed("A", {}) == 15
    assert budget.headroom_needed("H1", {"A": 4.0}) == 6.0


def test_cli_reads_state(tmp_path, capsys):
    p = tmp_path / "state.json"
    p.write_text(json.dumps({"arm_costs_usd": {"A": 6.0}}))
    rc = budget.main(["--state", str(p), "--arm", "H3", "--cost", "10"])
    assert rc == 2
    assert "capped" in capsys.readouterr().out
