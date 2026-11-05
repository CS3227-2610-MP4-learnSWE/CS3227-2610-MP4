import unittest
from pathlib import Path

from tracker.model import UsageRow
from tracker.pricing import cost_breakdown, cost_usd, load_prices, resolve_model_prices

REAL_PRICES = Path(__file__).resolve().parent.parent / "prices.json"
HAIKU = {
    "match_variants": True,
    "tiers": [
        {"max_prompt_tokens": 100000, "input": 0.10, "cache_write_5m": 0.125, "cache_write_1h": 0.20, "cache_read": 0.01, "output": 0.50},
        {"input": 0.50, "cache_write_5m": 0.625, "cache_write_1h": 1.00, "cache_read": 0.05, "output": 2.50},
    ],
}
FLAT = {"input": 3.0, "cache_read": 0.3, "cache_write_5m": 3.75, "cache_write_1h": 6.0, "output": 15.0}


def row(model="claude-haiku-5-5", inp=0, cr=0, w5=0, w1=0, out=0):
    return UsageRow(
        tool="claude", session_id="s", agent_id="", agent_type="main", is_subagent=False, model=model, branch="b",
        cwd="c", timestamp="2026-11-01T00:00:00Z", input_tokens=inp, cache_read_tokens=cr, cache_write_5m_tokens=w5,
        cache_write_1h_tokens=w1, output_tokens=out, reasoning_tokens=0,
    )


PRICES = {"models": {"claude-haiku-5-5": HAIKU, "flat": FLAT}}


class PricingTest(unittest.TestCase):
    def test_trk03_haiku_entry_in_prices_json(self):  # AC1
        entry = load_prices(REAL_PRICES)["models"]["claude-haiku-5-5"]
        self.assertEqual(entry["as_of"], "2026-11-05")
        self.assertIn("pricing page", entry["source"].lower())
        first, second = entry["tiers"]
        self.assertEqual(first["max_prompt_tokens"], 100000)
        self.assertEqual(
            {k: first[k] for k in ("input", "cache_write_5m", "cache_write_1h", "cache_read", "output")},
            {"input": 0.10, "cache_write_5m": 0.125, "cache_write_1h": 0.20, "cache_read": 0.01, "output": 0.50},
        )
        self.assertNotIn("max_prompt_tokens", second)
        self.assertEqual(
            {k: second[k] for k in ("input", "cache_write_5m", "cache_write_1h", "cache_read", "output")},
            {"input": 0.50, "cache_write_5m": 0.625, "cache_write_1h": 1.00, "cache_read": 0.05, "output": 2.50},
        )

    def test_trk03_haiku_tier_boundary_100000_first_tier(self):  # AC2
        self.assertAlmostEqual(cost_usd(row(inp=100000), PRICES), 100000 * 0.10 / 1e6)

    def test_trk03_haiku_100001_second_tier(self):  # AC2
        self.assertAlmostEqual(cost_usd(row(inp=100001), PRICES), 100001 * 0.50 / 1e6)

    def test_trk03_prompt_size_counts_cache_reads_and_both_writes(self):  # AC2
        r = row(inp=50000, cr=30000, w5=10000, w1=10001, out=1000)
        expected = (50000 * 0.50 + 30000 * 0.05 + 10000 * 0.625 + 10001 * 1.0 + 1000 * 2.5) / 1e6
        self.assertEqual(r.prompt_tokens, 100001)
        self.assertAlmostEqual(cost_usd(r, PRICES), expected)
        at_limit = row(inp=50000, cr=30000, w5=10000, w1=10000, out=1000)
        expected_first = (50000 * 0.10 + 30000 * 0.01 + 10000 * 0.125 + 10000 * 0.20 + 1000 * 0.50) / 1e6
        self.assertAlmostEqual(cost_usd(at_limit, PRICES), expected_first)

    def test_trk03_output_tokens_do_not_choose_the_tier(self):  # AC2
        self.assertAlmostEqual(cost_usd(row(inp=10, out=500000), PRICES), (10 * 0.10 + 500000 * 0.50) / 1e6)

    def test_trk03_flat_entry_unchanged(self):  # AC3
        r = row(model="flat", inp=1_000_000, cr=1_000_000, w5=1_000_000, w1=1_000_000, out=1_000_000)
        self.assertAlmostEqual(cost_usd(r, PRICES), 3.0 + 0.3 + 3.75 + 6.0 + 15.0)

    def test_trk03_sonnet_opus_costs_unchanged(self):  # AC3
        prices = load_prices(REAL_PRICES)
        everything = dict(inp=1_000_000, cr=1_000_000, w5=1_000_000, w1=1_000_000, out=1_000_000)
        self.assertAlmostEqual(cost_usd(row("claude-sonnet-5-5", **everything), prices), 2.0 + 0.1 + 2.5 + 4.0 + 10.0)
        self.assertAlmostEqual(cost_usd(row("claude-opus-5-5", **everything), prices), 4.0 + 0.2 + 5.0 + 8.0 + 20.0)

    def test_trk03_unknown_model_cost_none(self):  # AC3
        self.assertIsNone(cost_usd(row(model="other", inp=1), PRICES))

    def test_trk03_malformed_tiers_cost_none(self):  # AC3
        for tiers in ("text", [], [1], [{"max_prompt_tokens": "100", "input": 1, "output": 1}]):
            prices = {"models": {"m": {"tiers": tiers}}}
            self.assertIsNone(cost_usd(row(model="m", inp=10, out=10), prices), tiers)

    def test_trk03_no_applicable_tier_cost_none(self):  # AC3
        tier = {"max_prompt_tokens": 10, "input": 1, "cache_read": 1, "cache_write_5m": 1, "cache_write_1h": 1, "output": 1}
        self.assertIsNone(cost_usd(row(model="m", inp=100), {"models": {"m": {"tiers": [tier]}}}))

    def test_trk03_tiers_win_over_flat_keys(self):  # AC3
        entry = dict(FLAT, tiers=HAIKU["tiers"])
        self.assertAlmostEqual(cost_usd(row(model="m", inp=1000), {"models": {"m": entry}}), 1000 * 0.10 / 1e6)

    def test_trk03_cost_breakdown_sums_to_cost_usd(self):  # AC3
        r = row(inp=1000, cr=2000, w5=3000, w1=4000, out=500)
        parts = cost_breakdown(r, PRICES)
        self.assertEqual(list(parts), ["input", "cache_read", "cache_write_5m", "cache_write_1h", "output"])
        total = 0.0
        for value in parts.values():
            total += value
        self.assertEqual(total, cost_usd(r, PRICES))

    def test_trk03_cost_breakdown_zero_tokens_and_none(self):  # AC3
        self.assertEqual(cost_breakdown(row(inp=10), PRICES)["output"], 0.0)
        self.assertIsNone(cost_breakdown(row(model="other", inp=1), PRICES))
        only_io = {"models": {"m": {"input": 1.0, "output": 1.0}}}
        self.assertIsNone(cost_breakdown(row(model="m", cr=5), only_io))
        self.assertEqual(cost_breakdown(row(model="m", inp=1, out=1), only_io)["cache_read"], 0.0)

    def test_trk03_haiku_dated_variant_priced_as_haiku(self):  # AC26
        self.assertIs(resolve_model_prices(PRICES, "claude-haiku-5-5-20261105"), HAIKU)
        self.assertAlmostEqual(cost_usd(row("claude-haiku-5-5-20261105", inp=1000), PRICES), 1000 * 0.10 / 1e6)

    def test_trk03_haiku_bracket_suffix_priced(self):  # AC26
        self.assertIs(resolve_model_prices(PRICES, "claude-haiku-5-5[1m]"), HAIKU)

    def test_trk03_haiku_5_50_not_priced(self):  # AC26
        self.assertIsNone(resolve_model_prices(PRICES, "claude-haiku-5-50"))
        self.assertIsNone(cost_usd(row("claude-haiku-5-50", inp=1), PRICES))

    def test_trk03_haiku_5_5x_not_priced(self):  # AC26
        self.assertIsNone(resolve_model_prices(PRICES, "claude-haiku-5-5x"))

    def test_trk03_other_haiku_version_and_provider_prefix_not_priced(self):  # AC26
        for model in ("claude-haiku-4-5", "anthropic.claude-haiku-5-5", "CLAUDE-HAIKU-5-5-1", "claude-haiku-5-5", None):
            if model == "claude-haiku-5-5":
                self.assertIs(resolve_model_prices(PRICES, model), HAIKU)
            elif model is not None:
                self.assertIsNone(resolve_model_prices(PRICES, model), model)

    def test_trk03_sonnet_variant_not_priced(self):  # AC26
        prices = load_prices(REAL_PRICES)
        self.assertIsNone(resolve_model_prices(prices, "claude-sonnet-5-5-20261105"))
        self.assertIsNotNone(resolve_model_prices(prices, "claude-sonnet-5-5"))
        self.assertIsNone(resolve_model_prices(prices, "claude-opus-5-5[1m]"))

    def test_trk03_match_variants_must_be_json_true(self):  # AC26
        prices = {"models": {"k": {"match_variants": "yes", "input": 1, "output": 1}}}
        self.assertIsNone(resolve_model_prices(prices, "k-1"))

    def test_trk03_exact_key_beats_variant_and_longest_marked_key_wins(self):  # AC26
        exact = {"input": 1, "output": 1}
        short = {"match_variants": True, "input": 2, "output": 2}
        long = {"match_variants": True, "input": 3, "output": 3}
        prices = {"models": {"a": short, "a-b": long, "a-b-exact": exact}}
        self.assertIs(resolve_model_prices(prices, "a-b-exact"), exact)
        self.assertIs(resolve_model_prices(prices, "a-b-c"), long)
        self.assertIs(resolve_model_prices(prices, "a-z"), short)
        self.assertIsNone(resolve_model_prices(prices, "ab"))


if __name__ == "__main__":
    unittest.main()
