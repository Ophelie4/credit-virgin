from datetime import datetime, timezone

from app.services import verification as v


def tx(i, day, direction, amount, balance=None, category="other", doc="a", doc_type="bank_statement", month=3, **kw):
    return {"id": i, "document_id": doc, "doc_type": doc_type, "time": datetime(2024, month, day, 12, tzinfo=timezone.utc),
            "description": kw.get("description", ""), "direction": direction, "amount": amount, "fee": kw.get("fee", 0),
            "balance": balance, "category": category, "counterparty": kw.get("counterparty")}


def test_balances_that_add_up_pass():
    rows = [tx(1, 1, "in", 500, 1500), tx(2, 2, "out", 200, 1300), tx(3, 3, "out", 100, 1190, fee=10)]
    c = v.balance_continuity({"a": rows}, {"a": {"opening_balance": 1000}})
    assert c.status == "pass"


def test_an_edited_balance_fails():
    rows = [tx(1, 1, "in", 500, 1500), tx(2, 2, "out", 200, 1900)]  # should be 1300
    c = v.balance_continuity({"a": rows}, {"a": {"opening_balance": 1000}})
    assert c.status in ("warn", "fail")
    assert "expected 1,300" in c.detail


def test_matching_rent_receipts_pass():
    rows = [tx(1, 5, "out", 120_000, category="rent"),
            tx(2, 5, "out", 120_000, category="rent", doc="r", doc_type="rent_receipts")]
    assert v.rent_receipts_vs_payments(rows).status == "pass"


def test_inflated_rent_receipts_fail_and_say_why():
    stmt = [tx(i, 5, "out", 120_000, category="rent", month=m) for i, m in enumerate((9, 10, 11, 12), 1)]
    fake = [tx(10 + i, 5, "out", 150_000, category="rent", doc="r", doc_type="rent_receipts", month=m)
            for i, m in enumerate((9, 10, 11, 12))]
    c = v.rent_receipts_vs_payments(stmt + fake)
    assert c.status == "fail"
    assert "receipt says 150,000, statement shows 120,000" in c.detail


def test_receipts_outside_the_statement_period_are_not_held_against_you():
    stmt = [tx(1, 5, "out", 120_000, category="rent", month=9)]
    old = [tx(2, 5, "out", 999, category="rent", doc="r", doc_type="rent_receipts", month=1)]
    assert v.rent_receipts_vs_payments(stmt + old).status == "skip"


def test_transfer_between_own_accounts_matches():
    rows = [tx(1, 10, "out", 50_000, category="transfer_out", doc="bank"),
            tx(2, 11, "in", 50_000, category="transfer_in", doc="momo")]
    assert v.internal_transfers(rows).status == "pass"


def test_transfer_that_never_arrives_fails():
    rows = [tx(1, 10, "out", 50_000, category="transfer_out", doc="bank"),
            tx(2, 20, "in", 70_000, category="transfer_in", doc="momo")]
    assert v.internal_transfers(rows).status == "fail"


def test_monthly_salary_is_regular():
    rows = [tx(i, 25, "in", 400_000, category="salary", month=m, counterparty="Imena Ltd") for i, m in enumerate(range(1, 7), 1)]
    assert v.salary_regularity(rows).status == "pass"


def test_salary_on_random_days_is_flagged():
    days = [(1, 3), (2, 27), (4, 2), (4, 30), (6, 15), (7, 1)]
    rows = [tx(i, d, "in", 400_000, category="salary", month=m) for i, (m, d) in enumerate(days, 1)]
    assert v.salary_regularity(rows).status == "warn"
