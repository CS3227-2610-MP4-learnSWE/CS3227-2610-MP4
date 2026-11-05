"""Blind labels for the grader run: x1..xN map to arms; the key stays in grading/key.json."""
import json
import random
from pathlib import Path


def make_key(arms, seed):
    if len(set(arms)) != len(arms):
        raise ValueError("duplicate arms")
    shuffled = list(arms)
    random.Random(seed).shuffle(shuffled)
    return {f"x{i}": arm for i, arm in enumerate(shuffled, 1)}


def reveal(key, label):
    return key[label]


def write_key(path, key):
    with Path(path).open("x", encoding="utf-8") as f:
        json.dump(key, f, indent=2)


def grader_labels(key):
    return sorted(key)
