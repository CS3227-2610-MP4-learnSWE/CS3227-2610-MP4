import unittest
from html.parser import HTMLParser
from types import SimpleNamespace

from compare import build_row
from html_report import agent_costs, bucket_costs, render_html, scatter, stacked_bars

PRICES = {"models": {"m": {"input": 1.0, "cache_read": 0.1, "cache_write_5m": 2.0, "cache_write_1h": 4.0, "output": 10.0}}}
TOTAL = {"requests": 3, "input_tokens": 100, "cache_read_tokens": 1000, "cache_write_5m_tokens": 10,
         "cache_write_1h_tokens": 20, "output_tokens": 50, "reasoning_tokens": 5, "cost_usd": 0.5}
GRADE = {"grader": {"passed": 17, "total": 18}, "own_tests": {"passed": 5, "total": 5}}


def usage(model="m", **kw):
    base = dict(model=model, input_tokens=1_000_000, cache_read_tokens=1_000_000, cache_write_5m_tokens=1_000_000,
                cache_write_1h_tokens=1_000_000, output_tokens=1_000_000)
    base.update(kw)
    return SimpleNamespace(**base)


class Collector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)


class HtmlReportTest(unittest.TestCase):
    def test_bucket_costs_merge_cache_writes_and_skip_unpriced(self):
        costs = bucket_costs([usage(), usage(model="unknown")], PRICES)
        self.assertEqual(costs, {"Uncached input": 1.0, "Cache read": 0.1, "Cache write": 6.0, "Output": 10.0})

    def test_agent_costs_sum_models_and_treat_unpriced_as_zero(self):
        groups = [{"agent_type": "main", "cost_usd": 1.0}, {"agent_type": "main", "cost_usd": 2.0},
                  {"agent_type": "verifier", "cost_usd": None}]
        self.assertEqual(agent_costs(groups), {"main": 3.0, "verifier": 0.0})

    def test_charts_show_notice_when_there_is_no_data(self):
        self.assertIn("No data yet", stacked_bars([("A", {})], ["x"]))
        self.assertIn("No graded runs", scatter([("A", None, None)]))

    def test_chart_labels_are_escaped(self):
        svg = stacked_bars([("<script>", {"x": 2.0})], ["x"])
        self.assertNotIn("<script>", svg)
        self.assertIn("&lt;script&gt;", svg)

    def test_full_page_is_well_formed_and_has_all_sections(self):
        table = [build_row(name, TOTAL, GRADE, {"revision_rounds": 1}) for name in ("A", "B", "baseline")]
        buckets = {r["run"]: {"Uncached input": 0.1, "Cache read": 0.1, "Cache write": 0.1, "Output": 0.2} for r in table}
        agents = {r["run"]: {"main": 0.3, "verifier": 0.2} for r in table}
        page = render_html(table, buckets, agents, "2026-10-29 12:00")
        parser = Collector()
        parser.feed(page)
        self.assertGreaterEqual(parser.tags.count("svg"), 3)
        self.assertEqual(parser.tags.count("section"), 6)
        for text in ("STU-02 workflow comparison", "Where the cost went", "Cost by agent", "Quality against cost", "94.4%"):
            self.assertIn(text, page)

    def test_page_renders_with_no_data_at_all(self):
        empty = {"requests": 0, "input_tokens": 0, "cache_read_tokens": 0, "cache_write_5m_tokens": 0,
                 "cache_write_1h_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0, "cost_usd": 0.0}
        table = [build_row(name, empty, None, {}) for name in ("A", "B", "baseline")]
        page = render_html(table, {}, {})
        self.assertIn("No data yet", page)
        self.assertIn("No graded runs", page)


if __name__ == "__main__":
    unittest.main()
