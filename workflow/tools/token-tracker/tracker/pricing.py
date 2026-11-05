"""Cost from a user-supplied price table (USD per million tokens)."""

from __future__ import annotations

import json
import string
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
_ALNUM = frozenset(string.ascii_letters + string.digits)


def load_prices(path: Path | None) -> dict:
    if path is None:
        return {"models": {}}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    data.setdefault("models", {})
    return data


def resolve_model_prices(prices: dict, model: str) -> dict | None:
    """The price entry for a model ID: an exact key, else the longest `match_variants` key it extends.

    A variant ID is a priced key followed by a character that is not an ASCII letter or digit
    (`claude-haiku-5-5-20261105`, `claude-haiku-5-5[1m]`), so `claude-haiku-5-50` does not match.
    """
    if not isinstance(model, str):
        return None
    models = prices.get("models", {})
    if model in models:
        return models[model] or None
    best = None
    for key, entry in models.items():
        if not (isinstance(entry, dict) and entry.get("match_variants") is True):
            continue
        if len(model) > len(key) and model.startswith(key) and model[len(key)] not in _ALNUM:
            if best is None or len(key) > len(best[0]):
                best = (key, entry)
    return best[1] if best else None


def cost_breakdown(row: UsageRow, prices: dict) -> dict[str, float] | None:
    """Cost per token type, or None if the model, its tier or any needed price is unknown."""
    entry = resolve_model_prices(prices, row.model)
    rates = _rates(entry, row.prompt_tokens) if entry else None
    if rates is None:
        return None
    parts: dict[str, float] = {}
    for field, key in _BUCKETS:
        tokens = getattr(row, field)
        if tokens == 0:
            parts[key] = 0.0
            continue
        if key not in rates:
            return None
        parts[key] = tokens * rates[key] / 1_000_000
    return parts


def cost_usd(row: UsageRow, prices: dict) -> float | None:
    """Cost of the row, or None if its model or any needed price is unknown."""
    parts = cost_breakdown(row, prices)
    if parts is None:
        return None
    total = 0.0
    for value in parts.values():
        total += value
    return total


def _rates(entry: dict, prompt_tokens: int) -> dict | None:
    """Flat entries are their own rates; tiered entries give the first tier that fits the prompt size."""
    if "tiers" not in entry:
        return entry
    tiers = entry["tiers"]
    if not isinstance(tiers, list) or not tiers:
        return None
    for tier in tiers:
        if not isinstance(tier, dict):
            return None
        limit = tier.get("max_prompt_tokens")
        if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int)):
            return None
    for tier in tiers:
        limit = tier.get("max_prompt_tokens")
        if limit is None or prompt_tokens <= limit:
            return tier
    return None
