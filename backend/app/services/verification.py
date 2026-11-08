"""Cross-document consistency checks: the trust layer.

Each check looks for agreement between independent documents, or internal consistency within one.
Statuses: pass / warn / fail / skip (not enough data to run).
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, timedelta

from ..models import Check

Tx = dict  # row from transactions table


def _near(a: float, b: float, tol: float = 0.01) -> bool:
    return abs(a - b) <= max(abs(b) * tol, 1)


def _within(d1: date, d2: date, days: int) -> bool:
    return abs((d1 - d2).days) <= days


def balance_continuity(txs_by_doc: dict[str, list[Tx]], docs: dict[str, dict]) -> Check:
    """Within each statement, balance[i] should equal balance[i-1] + in - out - fee."""
    checked, breaks, examples = 0, 0, []
    for doc_id, rows in txs_by_doc.items():
        rows = sorted(rows, key=lambda r: (r["time"], r["id"]))
        prev = docs[doc_id].get("opening_balance")
        for r in rows:
            if r["balance"] is None:
                continue
            if prev is not None:
                expected = float(prev) + (float(r["amount"]) if r["direction"] == "in" else -float(r["amount"]) - float(r["fee"] or 0))
                checked += 1
                if not _near(expected, float(r["balance"]), 0.005):
                    breaks += 1
                    if len(examples) < 2:
                        examples.append(f"{r['time'].date()} '{(r['description'] or '')[:40]}' expected {expected:,.0f}, shows {float(r['balance']):,.0f}")
            prev = r["balance"]
    if checked == 0:
        return Check(key="balance_continuity", label="Running balances add up", status="skip",
                     detail="No documents with running balances.")
    if breaks == 0:
        return Check(key="balance_continuity", label="Running balances add up", status="pass",
                     detail=f"All {checked} balance rows reconcile row by row. No signs of edited figures.")
    status = "fail" if breaks > 2 or breaks / checked > 0.05 else "warn"
    return Check(key="balance_continuity", label="Running balances add up", status=status,
                 detail=f"{breaks} of {checked} rows don't reconcile: " + "; ".join(examples))


def internal_transfers(all_txs: list[Tx]) -> Check:
    """Money leaving one of the applicant's accounts should arrive in another within 2 days."""
    outs = [t for t in all_txs if t["category"] == "transfer_out" and t["direction"] == "out"]
    ins = [t for t in all_txs if t["category"] == "transfer_in" and t["direction"] == "in"]
    if not outs or not ins:
        return Check(key="internal_transfers", label="Transfers between accounts match", status="skip",
                     detail="Need at least two accounts with transfers between them.")
    matched, unmatched = 0, []
    used = set()
    for o in outs:
        hit = next((i for i in ins if i["id"] not in used and i["document_id"] != o["document_id"]
                    and _near(float(i["amount"]), float(o["amount"])) and _within(i["time"].date(), o["time"].date(), 2)), None)
        if hit:
            matched += 1
            used.add(hit["id"])
        else:
            unmatched.append(o)
    if not unmatched:
        return Check(key="internal_transfers", label="Transfers between accounts match", status="pass",
                     detail=f"{matched} transfer(s) out of one account were received in another on the same dates and amounts.")
    status = "warn" if matched else "fail"
    ex = unmatched[0]
    return Check(key="internal_transfers", label="Transfers between accounts match", status=status,
                 detail=f"{matched} matched, {len(unmatched)} not found in any other document (e.g. {float(ex['amount']):,.0f} on {ex['time'].date()}).")


def rent_receipts_vs_payments(all_txs: list[Tx]) -> Check:
    """Each rent receipt inside the period covered by statements should match a rent payment within 3 days."""
    receipts = [t for t in all_txs if t["doc_type"] == "rent_receipts" and t["category"] == "rent"]
    stmts = [t for t in all_txs if t["doc_type"] != "rent_receipts"]
    payments = [t for t in stmts if t["category"] == "rent" and t["direction"] == "out"]
    if not receipts or not stmts:
        return Check(key="rent_match", label="Rent receipts match actual payments", status="skip",
                     detail="Need both rent receipts and a statement showing the payments.")
    lo = min(t["time"].date() for t in stmts) - timedelta(days=3)
    hi = max(t["time"].date() for t in stmts) + timedelta(days=3)
    in_window = [r for r in receipts if lo <= r["time"].date() <= hi]
    outside = len(receipts) - len(in_window)
    if not in_window:
        return Check(key="rent_match", label="Rent receipts match actual payments", status="skip",
                     detail=f"{len(receipts)} receipts fall outside the period covered by statements, so they can't be cross-checked.")
    matched, mismatched = 0, []
    for rc in in_window:
        same_day = [p for p in payments if _within(p["time"].date(), rc["time"].date(), 3)]
        if any(_near(float(p["amount"]), float(rc["amount"])) for p in same_day):
            matched += 1
        elif same_day:
            mismatched.append(f"{rc['time'].date()}: receipt says {float(rc['amount']):,.0f}, statement shows {float(same_day[0]['amount']):,.0f}")
        else:
            mismatched.append(f"{rc['time'].date()}: receipt for {float(rc['amount']):,.0f} has no matching payment")
    tail = f" {outside} earlier receipt(s) predate the statements and were not cross-checked." if outside else ""
    if not mismatched:
        return Check(key="rent_match", label="Rent receipts match actual payments", status="pass",
                     detail=f"All {matched} receipts in the statement period match a payment of the same amount within 3 days.{tail}")
    status = "fail" if len(mismatched) >= 2 or matched == 0 else "warn"
    return Check(key="rent_match", label="Rent receipts match actual payments", status=status,
                 detail=f"{matched} matched, {len(mismatched)} did not: " + "; ".join(mismatched[:2]) + "." + tail)


def salary_regularity(all_txs: list[Tx]) -> Check:
    """Salary should arrive about monthly, around the same day, from the same payer."""
    sal = sorted([t for t in all_txs if t["category"] == "salary" and t["direction"] == "in"], key=lambda t: t["time"])
    # de-duplicate salary seen in two documents on the same day (same money, two statements)
    seen, uniq = set(), []
    for t in sal:
        k = (t["time"].date(), round(float(t["amount"])))
        if k not in seen:
            seen.add(k)
            uniq.append(t)
    if len(uniq) < 2:
        return Check(key="salary_regularity", label="Income arrives regularly", status="skip",
                     detail="Fewer than two salary credits found.")
    days = [t["time"].day for t in uniq]
    gaps = [(uniq[i + 1]["time"].date() - uniq[i]["time"].date()).days for i in range(len(uniq) - 1)]
    payers = {re.sub(r"[^a-z]", "", (t["counterparty"] or "").lower())[:12] for t in uniq if t["counterparty"]}
    regular = all(25 <= g <= 36 for g in gaps) and (max(days) - min(days) <= 5)
    if regular:
        return Check(key="salary_regularity", label="Income arrives regularly", status="pass",
                     detail=f"{len(uniq)} salary credits, roughly monthly around day {round(sum(days)/len(days))}"
                            + (f", from {len(payers)} payer." if payers else "."))
    return Check(key="salary_regularity", label="Income arrives regularly", status="warn",
                 detail=f"{len(uniq)} salary credits with uneven timing (gaps of {min(gaps)}–{max(gaps)} days).")


def run_all(all_txs: list[Tx], docs: dict[str, dict]) -> list[Check]:
    by_doc: dict[str, list[Tx]] = defaultdict(list)
    for t in all_txs:
        by_doc[str(t["document_id"])].append(t)
    return [
        balance_continuity(by_doc, docs),
        rent_receipts_vs_payments(all_txs),
        internal_transfers(all_txs),
        salary_regularity(all_txs),
    ]
