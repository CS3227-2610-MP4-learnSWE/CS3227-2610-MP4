"""Cost from a user-supplied price table (USD per million tokens)."""

from __future__ import annotations

import json
from pathlib import Path

from .model import UsageRow

# (UsageRow field, price key). Reasoning tokens are a subset of output, so not priced.
_BUCKETS = [
    ("input_tokens", "input"),
    ("cache_read_tokens", "cache_read"),
    ("cache_write_5m_tokens", "cache_write_5m"),
    ("cache_write_1h_tokens", "cache_write_1h"),
    ("output_tokens", "output"),
]


def load_prices(path: Path | None) -> dict:
    if path is None:
        return {"models": {}}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    data.setdefault("models", {})
    return data


def cost_usd(row: UsageRow, prices: dict) -> float | None:
    """Cost of the row, or None if its model or any needed price is unknown."""
    model_prices = prices.get("models", {}).get(row.model)
    if not model_prices:
        return None
    total = 0.0
    for field, key in _BUCKETS:
        tokens = getattr(row, field)
        if tokens == 0:
            continue
        if key not in model_prices:
            return None
        total += tokens * model_prices[key] / 1_000_000
    return total
