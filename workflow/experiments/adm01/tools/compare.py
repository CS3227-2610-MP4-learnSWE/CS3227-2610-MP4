"""Decision rule: compare only qualified arms, % cost change vs A. Costs are list-price estimates, not billed."""
ADOPT_PCT = -10.0


def qualified(a):
    return (
        a.get("q1") is True
        and a.get("q2") is True
        and a.get("converged") is True
        and not a.get("capped")
    )


def pct_vs_a(cost, a_cost):
    if not a_cost:
        return None
    return (cost - a_cost) / a_cost * 100


def verdicts(arms):
    """Map each non-A arm to adopt / inconclusive / reject / not run / no verdict."""
    base = arms.get("A")
    out = {}
    for name, a in arms.items():
        if name == "A":
            continue
        if a is None:
            out[name] = "not run"
        elif not qualified(a):
            out[name] = "reject"
        elif base is None or not qualified(base) or a.get("cost_usd") is None or base.get("cost_usd") is None:
            out[name] = "no verdict"
        else:
            pct = pct_vs_a(a["cost_usd"], base["cost_usd"])
            if pct is None:
                out[name] = "no verdict"
            elif pct <= ADOPT_PCT:
                out[name] = "adopt"
            elif pct < 0:
                out[name] = "inconclusive"
            else:
                out[name] = "reject"
    return out
