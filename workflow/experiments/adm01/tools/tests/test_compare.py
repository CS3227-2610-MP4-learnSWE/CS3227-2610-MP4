import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import compare


def arm(cost, q1=True, q2=True, converged=True, capped=False):
    return {"cost_usd": cost, "q1": q1, "q2": q2, "converged": converged, "capped": capped}


def test_qualified_needs_all():
    assert compare.qualified(arm(5))
    for k in ("q1", "q2", "converged"):
        assert not compare.qualified(arm(5, **{k: False}))
    assert not compare.qualified(arm(5, capped=True))
    assert not compare.qualified(arm(5, q2=None))


def test_pct_change():
    assert compare.pct_vs_a(8.0, 10.0) == -20.0
    assert compare.pct_vs_a(8.0, 0) is None


def test_verdicts():
    arms = {
        "A": arm(10),
        "H1": arm(8),
        "H2": arm(9.5),
        "H3": arm(8, q1=False),
        "C": arm(12),
    }
    v = compare.verdicts(arms)
    assert v["H1"] == "adopt"
    assert v["H2"] == "inconclusive"
    assert v["H3"] == "reject"
    assert v["C"] == "reject"
    assert "A" not in v


def test_exactly_ten_percent_adopts():
    assert compare.verdicts({"A": arm(10), "H1": arm(9)})["H1"] == "adopt"


def test_not_run_has_no_verdict():
    assert compare.verdicts({"A": arm(10), "H1": None})["H1"] == "not run"


def test_unqualified_or_missing_a_gives_no_verdict():
    assert compare.verdicts({"A": arm(10, q1=False), "H1": arm(5)})["H1"] == "no verdict"
    assert compare.verdicts({"H1": arm(5)})["H1"] == "no verdict"


def test_unavailable_cost_is_no_verdict():
    assert compare.verdicts({"A": arm(10), "H1": arm(None)})["H1"] == "no verdict"
