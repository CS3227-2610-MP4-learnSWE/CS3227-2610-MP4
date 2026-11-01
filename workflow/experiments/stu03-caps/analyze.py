"""Summarise results/*.jsonl into the numbers the cap recommendation needs. Offline only."""
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CANDIDATE_CAPS = (150, 200, 300, 400, 500, 800)


def load(folder: Path) -> list[dict]:
    rows = []
    for f in sorted(folder.glob("phase*.jsonl")):
        rows += [json.loads(line) for line in f.read_text(encoding="utf-8").splitlines() if line]
    return rows


def pct(values: list[float], p: float) -> float:
    s = sorted(values)
    return s[min(len(s) - 1, int(round(p * (len(s) - 1))))]


def main(folder: Path) -> None:
    rows = [r for r in load(folder) if r.get("http") == 200 and r.get("usage")]
    lat = [r["latency_s"] for r in rows]
    print(f"successful chat calls: {len(rows)}")
    if lat:
        print(f"latency p50={statistics.median(lat):.2f}s p95={pct(lat, .95):.2f}s max={max(lat):.2f}s")
    print("\nOutput tokens by mode (phase 2, generous cap) and share cut off by each candidate cap")
    for mode in ("hint", "explain", "help"):
        outs = [r["usage"]["completion_tokens"] for r in rows if r["phase"] == "phase2" and r["mode"] == mode]
        if not outs:
            continue
        cut = {c: f"{sum(o > c for o in outs) / len(outs):.0%}" for c in CANDIDATE_CAPS}
        print(f"  {mode}: n={len(outs)} median={statistics.median(outs):.0f} p95={pct(outs, .95):.0f} max={max(outs)} cut={cut}")
    print("\nPrompt tokens by input size / history (phase 3)")
    for r in rows:
        if r["phase"] == "phase3":
            print(f"  {r['id']}: chars={r['input_chars']} hist={r['history_msgs']} prompt_tokens={r['usage']['prompt_tokens']}")
    print("\nPhase 4: replies flagged as possibly stating the correct choice (needs manual read)")
    for r in rows:
        if r["phase"] == "phase4":
            print(f"  {r['id']}: suspected={r.get('leak_suspected')}")
    other = [r for r in load(folder) if r.get("http") not in (200, None)]
    if other:
        print("\nNon-200 responses:", [(r["id"], r["http"], r.get("error")) for r in other])


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "results")
