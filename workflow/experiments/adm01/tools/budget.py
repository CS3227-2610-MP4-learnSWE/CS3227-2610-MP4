"""Arm cost caps for the ADM-01 experiment. Costs are tracker list-price estimates, not billed."""
import argparse
import json
from pathlib import Path

A_CAP_USD = 15
MAX_CAP_USD = 15
LATER_FACTOR = 1.5


def cap_for(arm, arm_costs):
    """Cap in USD for an arm, or None while arm A's cost is unknown."""
    if arm == "A":
        return A_CAP_USD
    a = arm_costs.get("A")
    if a is None:
        return None
    return min(LATER_FACTOR * a, MAX_CAP_USD)


def status(arm, cost, arm_costs):
    cap = cap_for(arm, arm_costs)
    if cap is None:
        return "unknown"
    return "ok" if cost <= cap else "capped"


def headroom_needed(arm, arm_costs):
    """USD-equivalent headroom to have before starting an arm (gate G3)."""
    return cap_for(arm, arm_costs)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--state", required=True)
    p.add_argument("--arm", required=True)
    p.add_argument("--cost", type=float, required=True)
    args = p.parse_args(argv)
    costs = json.loads(Path(args.state).read_text(encoding="utf-8")).get("arm_costs_usd", {})
    result = status(args.arm, args.cost, costs)
    print(f"{args.arm}: {result} (cost {args.cost}, cap {cap_for(args.arm, costs)})")
    return {"ok": 0, "unknown": 1, "capped": 2}[result]


if __name__ == "__main__":
    raise SystemExit(main())
