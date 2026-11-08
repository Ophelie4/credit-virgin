from app.services.scoring import band_for, compute_factors


def month(inflow=1000, outflow=800, saved=100):
    return {"inflow": inflow, "outflow": outflow, "saved": saved}


def summary(**kw):
    base = {"rent_months_expected": 12, "rent_months_paid": 12, "bill_months_expected": 12, "bill_months_paid": 12,
            "negative_balance_rows": 0, "has_balance": True}
    return {**base, **kw}


def points(factors, key):
    return next(f.points for f in factors if f.key == key)


def test_steady_saver_who_pays_everything_scores_excellent():
    score, factors = compute_factors([month() for _ in range(12)], summary())
    assert score >= 90
    assert band_for(score) == "Excellent"
    assert points(factors, "payment_consistency") == 30


def test_points_never_exceed_each_factor_maximum():
    _, factors = compute_factors([month() for _ in range(12)], summary())
    assert all(0 <= f.points <= f.max_points for f in factors)
    assert sum(f.max_points for f in factors) == 100


def test_bills_count_when_there_is_no_rent():
    """Someone living with family pays no rent; on-time bills should still earn most of the payment points."""
    _, with_bills = compute_factors([month()] * 12, summary(rent_months_paid=0))
    _, nothing = compute_factors([month()] * 12, summary(rent_months_paid=0, bill_months_paid=0))
    assert points(with_bills, "payment_consistency") == 24
    assert points(nothing, "payment_consistency") == 4
    assert "bills count instead" in next(f.detail for f in with_bills if f.key == "payment_consistency")


def test_missed_bills_lower_the_score_a_little():
    _, all_paid = compute_factors([month()] * 12, summary())
    _, half_bills = compute_factors([month()] * 12, summary(bill_months_paid=6))
    assert points(all_paid, "payment_consistency") - points(half_bills, "payment_consistency") == 4


def test_rent_receipts_alone_are_not_penalised_for_missing_bills():
    """With receipts but no statements, bills can't be measured, so rent alone carries the full 30."""
    _, factors = compute_factors([], summary(bill_months_expected=0, bill_months_paid=0))
    assert points(factors, "payment_consistency") == 30


def test_irregular_income_scores_lower_than_steady_income():
    steady, _ = compute_factors([month(1000)] * 6, summary(rent_months_expected=6, rent_months_paid=6,
                                                            bill_months_expected=6, bill_months_paid=6))
    jumpy, _ = compute_factors([month(v) for v in (200, 2400, 100, 1900, 300, 2100)],
                               summary(rent_months_expected=6, rent_months_paid=6, bill_months_expected=6, bill_months_paid=6))
    assert steady > jumpy


def test_no_data_gives_a_low_but_valid_score():
    score, factors = compute_factors([], summary(rent_months_expected=0, rent_months_paid=0,
                                                 bill_months_expected=0, bill_months_paid=0, has_balance=False))
    assert 0 <= score < 35
    assert band_for(score) == "Limited"


def test_band_cutoffs():
    assert [band_for(s) for s in (80, 79, 65, 50, 35, 34)] == ["Excellent", "Strong", "Strong", "Fair", "Building", "Limited"]
