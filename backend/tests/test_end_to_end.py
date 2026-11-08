"""The demo story, run offline: real sample PDFs -> offline parser -> guardrails -> checks -> score."""
from app.services import verification
from app.services.scoring import compute_factors, summarize_payments

from conftest import monthly, to_rows

GENUINE = ["kivupay_mobile_money_statement.pdf", "banque_umurage_releve_de_compte.pdf", "rent_payment_receipts_2024.pdf"]


def score_for(sample_doc, names):
    rows, meta = to_rows([sample_doc(n) for n in names])
    score, factors = compute_factors(monthly(rows), summarize_payments(rows))
    checks = {c.key: c for c in verification.run_all(rows, meta)}
    if any(c.status == "fail" for c in checks.values()):
        score = min(score, 45)
    return score, factors, checks


def test_each_sample_is_read_offline(sample_doc):
    kinds = {n: sample_doc(n) for n in GENUINE}
    assert kinds[GENUINE[0]].doc_type == "mobile_money"
    assert kinds[GENUINE[1]].doc_type == "bank_statement"
    assert kinds[GENUINE[2]].doc_type == "rent_receipts"
    assert all(len(d.transactions) >= 10 for d in kinds.values())


def test_genuine_documents_score_excellent_with_every_check_passing(sample_doc):
    score, factors, checks = score_for(sample_doc, GENUINE)
    assert score >= 80, [(f.key, f.points) for f in factors]
    assert {k: c.status for k, c in checks.items()} == {
        "balance_continuity": "pass", "rent_match": "pass", "internal_transfers": "pass", "salary_regularity": "pass"}


def test_tampered_receipts_are_caught_and_cap_the_score(sample_doc):
    score, _, checks = score_for(sample_doc, GENUINE[:2] + ["TAMPERED_rent_receipts_2024.pdf"])
    assert checks["rent_match"].status == "fail"
    assert "150,000" in checks["rent_match"].detail
    assert score <= 45
