"""Explainable cashflow trust score (0-100). Every point comes with a reason."""
from __future__ import annotations

from statistics import mean, pstdev

from ..models import ScoreFactor

# Recurring obligations that show someone pays what they owe, on time, every month.
BILL_CATEGORIES = {"utilities", "airtime", "loan_repayment", "education"}

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


def summarize_payments(txs: list[dict]) -> dict:
    """Rent and bill months from transaction rows (oldest first), as used by the payment-consistency factor."""
    # Months in which rent was expected = months covered by any statement; paid = months with a rent 'out' row
    stmt_months = {(t["time"].year, t["time"].month) for t in txs if t["doc_type"] != "rent_receipts"}
    rent_months = {(t["time"].year, t["time"].month) for t in txs if t["category"] == "rent" and t["direction"] == "out"}
    bill_months = {(t["time"].year, t["time"].month) for t in txs if t["category"] in BILL_CATEGORIES and t["direction"] == "out"}
    return {
        "rent_months_expected": len(stmt_months) if stmt_months else len(rent_months),
        "rent_months_paid": len(rent_months & stmt_months) if stmt_months else len(rent_months),
        "bill_months_expected": len(stmt_months),
        "bill_months_paid": len(bill_months & stmt_months),
        "negative_balance_rows": sum(1 for t in txs if t["balance"] is not None and float(t["balance"]) < 0),
        "has_balance": any(t["balance"] is not None for t in txs),
    }


def compute_factors(months: list[dict], tx_summary: dict) -> tuple[int, list[ScoreFactor]]:
    """
    months: rows from monthly_cashflow (inflow, outflow, rent_paid, saved, salary, min_balance), oldest first.
    tx_summary: {'rent_months_expected', 'rent_months_paid', 'bill_months_expected', 'bill_months_paid',
                 'negative_balance_rows', 'has_balance'}
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

    # 2. Payment consistency (30): rent and recurring bills paid month after month.
    # Bills (electricity, water, phone, loan instalments, school fees) count too, so someone who lives with
    # family and pays no rent can still show a payment history, the way credit bureaus now accept utility data.
    exp, paid = tx_summary.get("rent_months_expected", 0), tx_summary.get("rent_months_paid", 0)
    bill_exp = tx_summary.get("bill_months_expected", exp)
    bills = tx_summary.get("bill_months_paid", 0)
    bill_ratio = (bills / bill_exp) if bill_exp else None  # None: no statements, so bills can't be measured
    if exp and paid:
        ratio = paid / exp
        pts = round(30 * ratio) if bill_ratio is None else round(22 * ratio + 8 * bill_ratio)
        detail = f"Rent was paid in {paid} of {exp} months covered."
        if ratio == 1:
            detail += " No missed months."
        if bills:
            detail += f" Bills were paid in {bills} of {bill_exp} months."
    elif bills and bill_ratio:
        pts = round(24 * bill_ratio)
        detail = (f"No rent payments were found, so recurring bills count instead: paid in {bills} of {bill_exp} "
                  "months (utilities, phone, loan instalments or school fees).")
    else:
        pts, detail = 4, "No rent or recurring bill payments were found in the documents."
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
