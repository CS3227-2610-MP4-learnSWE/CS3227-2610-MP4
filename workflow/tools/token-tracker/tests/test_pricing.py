import json
import tempfile
import unittest
from pathlib import Path

from tracker.model import UsageRow
from tracker.pricing import cost_usd, load_prices

PRICES = {
    "models": {
        "m": {"input": 3.0, "cache_read": 0.3, "cache_write_5m": 3.75, "cache_write_1h": 6.0, "output": 15.0}
    }
}


def row(model="m", **kw):
    base = dict(
        tool="claude", session_id="s", agent_id="", agent_type="main", is_subagent=False,
        model=model, branch="b", cwd="c", timestamp="2026-10-29T00:00:00Z",
        input_tokens=1_000_000, cache_read_tokens=1_000_000, cache_write_5m_tokens=1_000_000,
        cache_write_1h_tokens=1_000_000, output_tokens=1_000_000, reasoning_tokens=0,
    )
    base.update(kw)
    return UsageRow(**base)


class PricingTest(unittest.TestCase):
    def test_known_model_cost(self):  # AC6
        self.assertAlmostEqual(cost_usd(row(), PRICES), 3.0 + 0.3 + 3.75 + 6.0 + 15.0)

    def test_unknown_model_is_blank(self):  # AC6
        self.assertIsNone(cost_usd(row(model="other"), PRICES))

    def test_missing_price_key_is_blank_not_zero(self):  # AC6
        partial = {"models": {"m": {"input": 1.0, "output": 1.0}}}
        self.assertIsNone(cost_usd(row(), partial))

    def test_load_prices_none_gives_empty(self):
        self.assertEqual(load_prices(None), {"models": {}})

    def test_load_prices_reads_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prices.json"
            path.write_text(json.dumps(PRICES), encoding="utf-8")
            self.assertEqual(load_prices(path)["models"]["m"]["output"], 15.0)

    def test_zero_token_buckets_do_not_need_a_price(self):  # AC6
        only_io = {"models": {"m": {"input": 1.0, "output": 1.0}}}
        r = row(cache_read_tokens=0, cache_write_5m_tokens=0, cache_write_1h_tokens=0)
        self.assertAlmostEqual(cost_usd(r, only_io), 2.0)


if __name__ == "__main__":
    unittest.main()
