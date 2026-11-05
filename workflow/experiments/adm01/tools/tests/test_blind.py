import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import blind


def test_labels_cover_arms_once():
    key = blind.make_key(["A", "H3", "H1"], seed=1)
    assert sorted(key) == ["x1", "x2", "x3"]
    assert sorted(key.values()) == ["A", "H1", "H3"]


def test_same_seed_same_key_and_empty_ok():
    assert blind.make_key(["A", "H3"], seed=5) == blind.make_key(["A", "H3"], seed=5)
    assert blind.make_key([], seed=1) == {}


def test_duplicate_arms_rejected():
    with pytest.raises(ValueError):
        blind.make_key(["A", "A"], seed=1)


def test_reveal_maps_back_and_unknown_label_fails():
    key = {"x1": "H1", "x2": "A"}
    assert blind.reveal(key, "x2") == "A"
    with pytest.raises(KeyError):
        blind.reveal(key, "x9")


def test_write_key_refuses_overwrite(tmp_path):
    p = tmp_path / "key.json"
    blind.write_key(p, {"x1": "A"})
    assert json.loads(p.read_text()) == {"x1": "A"}
    with pytest.raises(FileExistsError):
        blind.write_key(p, {"x1": "H1"})


def test_grader_view_hides_arm_names():
    assert blind.grader_labels({"x1": "A", "x2": "H1"}) == ["x1", "x2"]
