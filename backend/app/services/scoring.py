"""Explainable cashflow trust score (0-100). Every point comes with a reason."""
from __future__ import annotations

from statistics import mean, pstdev

from ..models import ScoreFactor

BANDS = [(80, "Excellent"), (65, "Strong"), (50, "Fair"), (35, "Building"), (0, "Limited")]


def band_for(score: int) -> str:
    for cutoff, name in BANDS:
        if score >= cutoff:
            return name
    return "Limited"


def _cv(values: list[float]) -> float:
    vals = [v for v in values if v is not None]
    if len(vals) < 2 or mean(vals) == 0:
        return 1.0
    return pstdev(vals) / mean(vals)


def compute_factors(months: list[dict], tx_summary: dict) -> tuple[int, list[ScoreFactor]]:
    """
    months: rows from monthly_cashflow (inflow, outflow, rent_paid, saved, salary, min_balance), oldest first.
    tx_summary: {'rent_months_expected': int, 'rent_months_paid': int, 'negative_balance_rows': int, 'has_balance': bool}
    """
    factors: list[ScoreFactor] = []
    n = len(months)
    inflows = [float(m.get("inflow") or 0) for m in months]
    outflows = [float(m.get("outflow") or 0) for m in months]
    saved = [float(m.get("saved") or 0) for m in months]

    # 1. Income stability (25): low month-to-month variation in inflow
    cv = _cv(inflows) if n >= 2 else 1.0
    if n < 2:
        pts, detail = 5, "Fewer than two months of inflow data, so stability can't be measured yet."
    elif cv < 0.15:
        pts, detail = 25, f"Monthly income varied by only {cv:.0%} across {n} months: very steady."
    elif cv < 0.35:
        pts, detail = 18, f"Monthly income varied by {cv:.0%} across {n} months: fairly steady."
    elif cv < 0.6:
        pts, detail = 10, f"Monthly income varied by {cv:.0%}: somewhat irregular."
    else:
        pts, detail = 4, f"Monthly income varied by {cv:.0%}: irregular."
    factors.append(ScoreFactor(key="income_stability", label="Income stability", points=pts, max_points=25, detail=detail))

    # 2. Payment consistency (30): rent paid every month it was expected
    exp, paid = tx_summary.get("rent_months_expected", 0), tx_summary.get("rent_months_paid", 0)
    if exp == 0:
        pts, detail = 8, "No rent payments were found in the documents."
    else:
        ratio = paid / exp
        pts = round(30 * ratio)
        detail = f"Rent was paid in {paid} of {exp} months covered."
        if ratio == 1:
            detail += " No missed months."
    factors.append(ScoreFactor(key="payment_consistency", label="Payment consistency", points=pts, max_points=30, detail=detail))

    # 3. Savings behaviour (15): share of income set aside
    total_in, total_saved = sum(inflows), sum(saved)
    rate = (total_saved / total_in) if total_in else 0
    if rate >= 0.15:
        pts, detail = 15, f"About {rate:.0%} of income went to savings: a strong habit."
    elif rate >= 0.08:
        pts, detail = 11, f"About {rate:.0%} of income went to savings."
    elif rate > 0:
        pts, detail = 6, f"About {rate:.0%} of income went to savings: a start."
    else:
        pts, detail = 2, "No savings transfers were identified."
    factors.append(ScoreFactor(key="savings", label="Savings behaviour", points=pts, max_points=15, detail=detail))

    # 4. Balance health (15): spending within means, no negative balances
    neg = tx_summary.get("negative_balance_rows", 0)
    surplus_months = sum(1 for i, o in zip(inflows, outflows) if i >= o)
    if n == 0:
        pts, detail = 3, "No monthly data yet."
    else:
        share = surplus_months / n
        pts = round(12 * share) + (3 if neg == 0 and tx_summary.get("has_balance") else 0)
        detail = f"Spent less than earned in {surplus_months} of {n} months."
        detail += " Balance never went negative." if (neg == 0 and tx_summary.get("has_balance")) else (f" Balance went negative on {neg} rows." if neg else "")
    factors.append(ScoreFactor(key="balance_health", label="Balance health", points=pts, max_points=15, detail=detail))

    # 5. History length (15): months of evidence
    if n >= 12:
        pts, detail = 15, f"{n} months of history: a full year of evidence."
    elif n >= 6:
        pts, detail = 11, f"{n} months of history."
    elif n >= 3:
        pts, detail = 7, f"{n} months of history: more documents would strengthen this."
    else:
        pts, detail = 3, f"Only {n} month(s) of history so far."
    factors.append(ScoreFactor(key="history", label="History length", points=pts, max_points=15, detail=detail))

    score = max(0, min(100, sum(f.points for f in factors)))
    return score, factors
