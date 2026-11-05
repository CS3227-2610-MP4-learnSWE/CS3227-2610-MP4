"""Render the arm comparison as a single self-contained HTML page."""
from html import escape


def _cell(v):
    if v is None:
        return "unavailable"
    return escape(str(v))


def render(arms, verdicts):
    rows = []
    for name, a in arms.items():
        if a is None:
            rows.append(f"<tr><td>{escape(name)}</td><td colspan='2'>not run</td></tr>")
            continue
        extra = ", ".join(f"{escape(k)}: {_cell(v)}" for k, v in a.items() if k != "cost_usd")
        rows.append(
            f"<tr><td>{escape(name)}</td><td>{_cell(a.get('cost_usd'))}</td>"
            f"<td>{escape(verdicts.get(name, ''))} {extra}</td></tr>"
        )
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<title>ADM-01 experiment</title></head><body><h1>ADM-01 experiment</h1>"
        "<table><tr><th>Arm</th><th>Cost (USD)</th><th>Verdict / details</th></tr>"
        + "".join(rows)
        + "</table><p>Costs are tracker list-price estimates, not billed.</p></body></html>"
    )
