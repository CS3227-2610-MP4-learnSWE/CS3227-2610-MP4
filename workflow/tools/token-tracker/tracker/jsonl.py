"""Tolerant JSON Lines reading shared by the log parsers."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path


def as_int(value) -> int:
    """Token counts are ints; anything else (missing, null, text) counts as 0."""
    return value if isinstance(value, int) else 0


def read_objects(path: Path) -> Iterator[dict]:
    """Yield each JSON object in the file, skipping blank and malformed lines."""
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                yield obj
