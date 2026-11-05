import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import grade_arm


def test_parse_all_passed():
    r = grade_arm.parse_summary("== 153 passed in 40.2s ==")
    assert r == {"passed": 153, "failed": 0, "errors": 0, "skipped": 0}


def test_parse_mixed():
    r = grade_arm.parse_summary("3 failed, 140 passed, 10 skipped, 1 error in 9s")
    assert r == {"passed": 140, "failed": 3, "errors": 1, "skipped": 10}


def test_parse_unrecognised_returns_none():
    assert grade_arm.parse_summary("no tests ran") is None
    assert grade_arm.parse_summary("") is None


def test_q1_requires_all_pass_no_skips():
    ok = {"passed": 153, "failed": 0, "errors": 0, "skipped": 0}
    assert grade_arm.q1_pass(ok, expected=153)
    assert not grade_arm.q1_pass({**ok, "skipped": 153, "passed": 0}, expected=153)
    assert not grade_arm.q1_pass({**ok, "failed": 1}, expected=153)
    assert not grade_arm.q1_pass({**ok, "passed": 152}, expected=153)
    assert not grade_arm.q1_pass(None, expected=153)


def test_install_frozen_copies_only_named_files(tmp_path):
    src = tmp_path / "frozen"
    dst = tmp_path / "arm" / "tests"
    src.mkdir()
    dst.mkdir(parents=True)
    (src / "test_adm01_report.py").write_text("a")
    (src / "other.py").write_text("b")
    grade_arm.install_frozen(src, dst, ["test_adm01_report.py"])
    assert (dst / "test_adm01_report.py").read_text() == "a"
    assert not (dst / "other.py").exists()


def test_grade_blocked_without_db_env(monkeypatch, tmp_path):
    monkeypatch.delenv("TEA01_TEST_DATABASE_URL", raising=False)
    r = grade_arm.grade(tmp_path, tmp_path, ["x.py"], expected=1, runner=lambda *_: "")
    assert r["status"] == "blocked"
    assert "TEA01_TEST_DATABASE_URL" in r["reason"]


def test_grade_with_fake_runner(monkeypatch, tmp_path):
    monkeypatch.setenv("TEA01_TEST_DATABASE_URL", "x")
    frozen = tmp_path / "f"
    frozen.mkdir()
    (frozen / "t.py").write_text("")
    arm = tmp_path / "arm"
    (arm / "src" / "backend" / "tests").mkdir(parents=True)
    r = grade_arm.grade(arm, frozen, ["t.py"], expected=2, runner=lambda *_: "2 passed in 1s")
    assert r["status"] == "done" and r["q1"] is True
    r = grade_arm.grade(arm, frozen, ["t.py"], expected=2, runner=lambda *_: "1 failed, 1 passed in 1s")
    assert r["q1"] is False
