"""Cost-effectiveness analysis of the phase 6 sweep. Offline only.

Per-token prices are not published to us, so they are fitted from phases 1-5: dashboard spend per phase against
that phase's prompt and completion token totals (least squares, two unknowns). The fit is an estimate; the
phase 6 total is checked against the dashboard afterwards.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent


def rows(folder: Path, name: str) -> list[dict]:
    path = folder / f"{name}.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line] if path.exists() else []


def fit_prices(folder: Path) -> tuple[float, float]:
    spend = json.loads((HERE / "dashboard.json").read_text())
    sxx = sxy = syy = bx = by = 0.0
    for phase in ("phase1", "phase2", "phase3", "phase4", "phase5"):
        us = [r["usage"] for r in rows(folder, phase) if r.get("usage")]
        x = sum(u["prompt_tokens"] for u in us)
        y = sum(u["completion_tokens"] for u in us)
        s = spend[phase]
        sxx += x * x; sxy += x * y; syy += y * y; bx += x * s; by += y * s
    det = sxx * syy - sxy * sxy
    pin, pout = (bx * syy - by * sxy) / det, (by * sxx - bx * sxy) / det
    if pin < 0 or pout < 0:
        raise SystemExit(f"Price fit gave a negative price ({pin}, {pout}); inspect the data before trusting it.")
    return pin, pout


def write_grid(folder: Path, data: list[dict], pin: float, pout: float) -> None:
    """Every combination (mode x cap x instruction x history): replies passing out of 3 and $ per 1,000 calls."""
    grid = {}
    for mode in ("hint", "explain", "help"):
        cells = defaultdict(list)
        for r in (x for x in data if x["mode"] == mode):
            cells[(r["max_tokens"], r["style"], r["history_msgs"])].append(r)
        grid[mode] = [
            dict(cap=cap, instruction="short-answer" if style == "brief" else "standard", history=h, passed=sum(x["useful"] for x in g), n=len(g),
                 cost_per_1000=round(1000 * sum(x["usage"]["prompt_tokens"] * pin + x["usage"]["completion_tokens"] * pout for x in g) / len(g), 3))
            for (cap, style, h), g in sorted(cells.items())
        ]
    (folder / "phase6-grid.json").write_text(json.dumps(grid, indent=1), encoding="utf-8")
    lines = ["# Phase 6: every combination", "",
             "Cell: replies passing the usefulness rule (of 3 questions) and cost in $ per 1,000 calls (prices fitted from the dashboard). Hint uses the relaxed rule (no question mark required).", ""]
    for mode, rows_ in grid.items():
        lines += [f"## {mode}", "", "| Cap | Standard, history 0 | Standard, history 2 | Standard, history 4 | Short-answer, history 0 | Short-answer, history 2 | Short-answer, history 4 |", "|---|---|---|---|---|---|---|"]
        for cap in sorted({r["cap"] for r in rows_}):
            cells_ = []
            for inst in ("standard", "short-answer"):
                for h in (0, 2, 4):
                    c = next(r for r in rows_ if r["cap"] == cap and r["instruction"] == inst and r["history"] == h)
                    cells_.append(f"{c['passed']}/{c['n']}, {c['cost_per_1000']:.3f}")
            lines.append(f"| {cap} | " + " | ".join(cells_) + " |")
        lines.append("")
    (folder / "phase6-grid.md").write_text("\n".join(lines), encoding="utf-8")
    print("wrote phase6-grid.md and phase6-grid.json")


def main(folder: Path) -> None:
    pin, pout = fit_prices(folder)
    print(f"fitted price per 1M tokens: input ${pin * 1e6:.3f}, output ${pout * 1e6:.3f} (estimate)")
    data = [r for r in rows(folder, "phase6") if r.get("usage")]
    if "--hint-no-question" in sys.argv:
        # Post-hoc rule (added after seeing the data): a hint need not contain a question mark.
        sys.path.insert(0, str(HERE))
        import cases
        import rules
        by_id = {c["id"]: c for c in cases.phase6_cases()}
        for r in data:
            if r["mode"] == "hint":
                r["useful"] = rules.useful(by_id[r["id"]], r, need_question=False)
        print("HINT RULE RELAXED: no question mark required (post-hoc)")
    if "--grid" in sys.argv:
        write_grid(folder, data, pin, pout)
    print(f"phase 6 calls: {len(data)}, estimated cost ${sum(r['usage']['prompt_tokens'] * pin + r['usage']['completion_tokens'] * pout for r in data):.4f}")
    for mode in ("hint", "explain", "help"):
        m = [r for r in data if r["mode"] == mode]
        if not m:
            continue
        groups = defaultdict(list)
        for r in m:
            groups[(r["max_tokens"], r["style"])].append(r)
        print(f"\n== {mode}: output cap x answer-length instruction (pooled over history 0/2/4 and 3 questions)")
        print("cap  style     useful  cut-off  prompt  output  $/call   $/useful")
        table = []
        for (cap, style), g in sorted(groups.items()):
            ok = sum(r["useful"] for r in g)
            cut = sum(r["finish_reason"] == "length" for r in g)
            pt = sum(r["usage"]["prompt_tokens"] for r in g) / len(g)
            ct = sum(r["usage"]["completion_tokens"] for r in g) / len(g)
            cost = pt * pin + ct * pout
            per_useful = cost * len(g) / ok if ok else float("inf")
            table.append((per_useful, ok, len(g), cap, style))
            print(f"{cap:<4} {style:<9} {ok}/{len(g):<5} {cut:<8} {pt:<7.0f} {ct:<7.0f} {cost:.6f}   {per_useful:.6f}")
        best = [t for t in sorted(table) if t[1] == t[2]]
        print("cheapest config where every reply was useful:", f"cap {best[0][3]}, {best[0][4]} prompt, ${best[0][0]:.6f} per useful reply" if best else "none")
        near = [t for t in sorted(table) if t[1] >= 0.9 * t[2]][:3]
        print("cheapest with at least 90% useful:", [(t[3], t[4], f"{t[1]}/{t[2]}", round(t[0], 6)) for t in near])
        print(f"-- {mode}: history effect (all caps and styles)")
        for h in (0, 2, 4):
            g = [r for r in m if r["history_msgs"] == h]
            if g:
                print(f"   history {h}: useful {sum(r['useful'] for r in g)}/{len(g)}, mean prompt tokens {sum(r['usage']['prompt_tokens'] for r in g) / len(g):.0f}")
    print("\n== Most cost-effective combination per mode: instruction x history, over the caps where that instruction passed (>= 8 of 9 pooled)")
    print("mode     instruction history  caps passing        useful  $/call    $/useful")
    for mode in ("hint", "explain", "help"):
        m = [r for r in data if r["mode"] == mode]
        best = None
        for style in ("standard", "brief"):
            by_cap = defaultdict(list)
            for r in m:
                if r["style"] == style:
                    by_cap[r["max_tokens"]].append(r)
            caps = sorted(c for c, g in by_cap.items() if sum(x["useful"] for x in g) >= 8)
            for h in (0, 2, 4):
                g = [r for c in caps for r in by_cap[c] if r["history_msgs"] == h]
                if not g:
                    continue
                ok = sum(r["useful"] for r in g)
                cost = sum(r["usage"]["prompt_tokens"] * pin + r["usage"]["completion_tokens"] * pout for r in g) / len(g)
                per_useful = cost * len(g) / ok if ok else float("inf")
                print(f"{mode:<8} {style:<11} {h:<8} {str(caps):<19} {ok}/{len(g):<5} {cost:.6f}  {per_useful:.6f}")
                if ok == len(g) and (best is None or per_useful < best[0]):
                    best = (per_useful, style, h)
        print(f"   cheapest combination with every reply useful: {best[1]} instruction, history {best[2]}, ${best[0]:.6f} per useful reply" if best else "   no combination with every reply useful")
    hints = [r for r in data if r["mode"] == "hint" and r.get("options_discussed") is not None]
    if hints:
        for style in ("standard", "brief"):
            g = [r for r in hints if r["style"] == style]
            print(f"\nhint narrowing signal, {style} prompt: mean options mentioned {sum(r['options_discussed'] for r in g) / len(g):.2f}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(Path(args[0]) if args else HERE / "results")
