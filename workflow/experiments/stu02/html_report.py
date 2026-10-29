"""Render the STU-02 comparison as one self-contained HTML page with inline SVG charts.

Pure functions: they take already-computed data and return text, so they are easy
to test. compare.py gathers the data and writes the file.
"""

from __future__ import annotations

from html import escape

BUCKETS = [
    ("input_tokens", "input", "Uncached input"),
    ("cache_read_tokens", "cache_read", "Cache read"),
    ("cache_write_5m_tokens", "cache_write_5m", "Cache write (5 min)"),
    ("cache_write_1h_tokens", "cache_write_1h", "Cache write (1 h)"),
    ("output_tokens", "output", "Output"),
]
BUCKET_SERIES = ["Uncached input", "Cache read", "Cache write", "Output"]
SERIES_OF = {key: ("Cache write" if key.startswith("cache_write") else label) for _, key, label in BUCKETS}
LABEL_W, BAR_X, BAR_W, ROW_H = 120, 130, 440, 34

STYLE = """
:root{--bg:#f7f8fb;--card:#fff;--text:#1b263b;--muted:#69758a;--line:#e1e6ef;
--c1:#2463eb;--c2:#c2410c;--c3:#0f766e;--c4:#7c3aed;--c5:#a16207;--c6:#be185d}
:root[data-theme=dark]{--bg:#10141d;--card:#191f2b;--text:#eef2fb;--muted:#a0acc1;--line:#2c3546;
--c1:#8aafff;--c2:#fb923c;--c3:#2dd4bf;--c4:#c4b5fd;--c5:#facc15;--c6:#f472b6}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#10141d;--card:#191f2b;--text:#eef2fb;
--muted:#a0acc1;--line:#2c3546;--c1:#8aafff;--c2:#fb923c;--c3:#2dd4bf;--c4:#c4b5fd;--c5:#facc15;--c6:#f472b6}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);
font:15px/1.5 system-ui,"Segoe UI",sans-serif}
main{max-width:860px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:1.5rem;margin:0 0 4px}h2{font-size:1.05rem;margin:0 0 4px}
p.sub{margin:0 0 20px;color:var(--muted)}
section{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin-bottom:16px}
section p{margin:0 0 10px;color:var(--muted);font-size:.9rem}
.chart{overflow-x:auto}svg{width:100%;min-width:560px;height:auto;display:block}svg text{fill:var(--text);font-size:12px}
svg .muted{fill:var(--muted)}svg .axis{stroke:var(--line)}
.legend{display:flex;flex-wrap:wrap;gap:4px 14px;margin:8px 0 0;padding:0;list-style:none;font-size:.85rem}
.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px}
.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:.85rem}
th,td{text-align:right;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:bottom}
td{white-space:nowrap}
th:first-child,td:first-child{text-align:left}th{color:var(--muted);font-weight:600}
.empty{color:var(--muted);font-style:italic}.note li{margin-bottom:4px}
"""


def fmt_money(value) -> str:
    return "n/a" if value is None else f"${value:,.2f}"


def fmt_num(value) -> str:
    return "n/a" if value is None else f"{value:,}"


def bucket_costs(rows: list, prices: dict) -> dict[str, float]:
    """Cost of a run split into four buckets. Requests with an unpriced model are skipped."""
    totals = {name: 0.0 for name in BUCKET_SERIES}
    for row in rows:
        model = prices.get("models", {}).get(row.model)
        if not model:
            continue
        for field, key, _ in BUCKETS:
            totals[SERIES_OF[key]] += getattr(row, field) * model.get(key, 0.0) / 1_000_000
    return totals


def agent_costs(groups: list[dict]) -> dict[str, float]:
    """Cost per agent type, summed over models. Unpriced groups count as 0."""
    totals: dict[str, float] = {}
    for group in groups:
        totals[group["agent_type"]] = totals.get(group["agent_type"], 0.0) + (group["cost_usd"] or 0.0)
    return totals


def _legend(names: list[str], colour_of) -> str:
    items = "".join(f'<li><i style="background:var({colour_of(n)})"></i>{escape(n)}</li>' for n in names)
    return f'<ul class="legend">{items}</ul>'


def stacked_bars(rows: list[tuple[str, dict[str, float]]], series: list[str], money: bool = True) -> str:
    """Horizontal stacked bars, one row per run; returns SVG plus legend, or a notice if all zero."""
    totals = [sum(parts.values()) for _, parts in rows]
    top = max(totals, default=0)
    if top <= 0:
        return '<p class="empty">No data yet.</p>'
    colour = lambda name: f"--c{series.index(name) % 6 + 1}"  # noqa: E731
    height = ROW_H * len(rows) + 8
    out = [f'<svg viewBox="0 0 640 {height}" role="img" aria-label="Stacked bar chart">']
    for i, ((label, parts), total) in enumerate(zip(rows, totals)):
        y, x = 4 + i * ROW_H, BAR_X
        out.append(f'<text x="0" y="{y + 19}">{escape(label)}</text>')
        for name in series:
            width = parts.get(name, 0.0) / top * BAR_W
            if width > 0:
                tip = f"{name}: {fmt_money(parts[name]) if money else fmt_num(int(parts[name]))}"
                out.append(f'<rect x="{x:.1f}" y="{y + 4}" width="{width:.1f}" height="22" fill="var({colour(name)})">'
                           f"<title>{escape(label)} - {escape(tip)}</title></rect>")
                x += width
        shown = fmt_money(total) if money else fmt_num(int(total))
        out.append(f'<text class="muted" x="{x + 6:.1f}" y="{y + 19}">{shown}</text>')
    out.append("</svg>")
    return f'<div class="chart">{"".join(out)}</div>' + (_legend(series, colour) if len(series) > 1 else "")


def scatter(points: list[tuple[str, float | None, float | None]]) -> str:
    """Cost (x) against grader percent (y) for runs that have both."""
    usable = [(n, x, y) for n, x, y in points if x is not None and y is not None]
    if not usable:
        return '<p class="empty">No graded runs with cost yet.</p>'
    max_x = max(x for _, x, _ in usable) * 1.2 or 1.0
    left, top, w, h = 50, 10, 540, 220
    out = [f'<svg viewBox="0 0 640 {h + 50}" role="img" aria-label="Grader score against cost">']
    for tick in (0, 25, 50, 75, 100):
        y = top + h - tick / 100 * h
        out.append(f'<line class="axis" x1="{left}" x2="{left + w}" y1="{y}" y2="{y}"/>'
                   f'<text class="muted" x="{left - 8}" y="{y + 4}" text-anchor="end">{tick}%</text>')
    out.append(f'<text class="muted" x="{left + w / 2}" y="{h + 40}" text-anchor="middle">Cost (USD)</text>')
    out.append(f'<text class="muted" x="{left}" y="{h + 24}" text-anchor="middle">$0</text>'
               f'<text class="muted" x="{left + w}" y="{h + 24}" text-anchor="end">{fmt_money(max_x)}</text>')
    for name, x, y in usable:
        cx, cy = left + x / max_x * w, top + h - y / 100 * h
        out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="7" fill="var(--c1)"><title>'
                   f"{escape(name)}: {fmt_money(x)}, {y:.1f}% of grader</title></circle>"
                   f'<text x="{cx + 11:.1f}" y="{cy + 4:.1f}">{escape(name)}</text>')
    out.append("</svg>")
    return f'<div class="chart">{"".join(out)}</div>'


def summary_table(rows: list[dict]) -> str:
    cols = [("Run", "run", str), ("Grader", "grader_pct", lambda v: "n/a" if v is None else f"{v}%"),
            ("Cost", "cost_usd", fmt_money), ("Total tokens", "total_tokens", fmt_num),
            ("Output tokens", "output_tokens", fmt_num), ("Requests", "requests", fmt_num),
            ("Cost per grader pass", "cost_per_grader_pass_usd", fmt_money),
            ("Revision rounds", "revision_rounds", fmt_num), ("Review min", "review_minutes", fmt_num),
            ("Quality 1-5", "quality_score", fmt_num)]
    head = "".join(f"<th>{escape(t)}</th>" for t, _, _ in cols)
    body = "".join("<tr>" + "".join(f"<td>{escape(str(f(r[k])))}</td>" for _, k, f in cols) + "</tr>" for r in rows)
    return f'<div class="scroll"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def render_html(table: list[dict], buckets: dict[str, dict[str, float]], agents: dict[str, dict[str, float]],
                generated: str = "") -> str:
    """The whole page. `table` rows come from compare.build_row."""
    bucket_rows = [(r["run"], buckets.get(r["run"], {})) for r in table]
    agent_names = sorted({a for per in agents.values() for a in per})
    agent_rows = [(r["run"], agents.get(r["run"], {})) for r in table]
    points = [(r["run"], r["cost_usd"] or None, r["grader_pct"]) for r in table]
    cost_rows = [(r["run"], {"Total cost": r["cost_usd"] or 0.0}) for r in table]
    notes = ["One run per condition: anecdotal evidence, not a statistical result.",
             "Usage is read from local logs by git branch and priced at API list prices (prices.json). "
             "Absolute totals are not checked against the Claude or Codex apps.",
             "Zero cost with no tokens means no usage was found for that branch yet."]
    sections = [
        ("Summary", "Everything on one line per run.", summary_table(table)),
        ("Total cost", "API-equivalent cost of each run, all agents and the orchestrating session.",
         stacked_bars(cost_rows, ["Total cost"])),
        ("Where the cost went", "Cost split by token type. Cache reads are most of the volume but cheap per token.",
         stacked_bars(bucket_rows, BUCKET_SERIES)),
        ("Cost by agent", "Shows the overhead of splitting work across agents. \"main\" is the orchestrating session.",
         stacked_bars(agent_rows, agent_names) if agent_names else '<p class="empty">No data yet.</p>'),
        ("Quality against cost", "Hidden grader score (y) against cost (x). Top left is better.", scatter(points)),
        ("Caveats", "", "<ul class=\"note\">" + "".join(f"<li>{escape(n)}</li>" for n in notes) + "</ul>"),
    ]
    blocks = "".join(f"<section><h2>{escape(t)}</h2>{'<p>' + escape(d) + '</p>' if d else ''}{body}</section>"
                     for t, d, body in sections)
    stamp = f" Generated {escape(generated)}." if generated else ""
    return ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>STU-02 workflow comparison</title>"
            f"<style>{STYLE}</style></head><body><main><h1>STU-02 workflow comparison</h1>"
            f"<p class=\"sub\">Split verification (A), merged verification (B) and the single-session baseline.{stamp}</p>"
            f"{blocks}</main></body></html>")
