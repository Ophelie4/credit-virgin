import datetime as dt

import pytest

from app.models import ExtractedDocument, ExtractedTransaction
from app.services.normalize import normalize


def doc(description, direction="out", category="other", doc_type="bank_statement"):
    t = ExtractedTransaction(date=dt.date(2024, 3, 1), description=description, direction=direction, amount=100,
                             category=category)
    return normalize(ExtractedDocument(source_name="Test", doc_type=doc_type, currency="RWF", language="en",
                                       transactions=[t])).transactions[0]


@pytest.mark.parametrize("description,direction,expected", [
    ("Salaire mars - Imena Ltd", "in", "salary"),
    ("Umushahara wa Werurwe", "in", "salary"),
    ("Paiement loyer mars", "out", "rent"),
    ("Ubukode bw'inzu", "out", "rent"),
    ("Ikimina contribution", "out", "savings"),
    ("Remboursement prêt", "out", "loan_repayment"),
    ("Transfer to own account", "out", "transfer_out"),
    ("Virement depuis mon compte", "in", "transfer_in"),
    ("Bill payment - electricity token", "out", "utilities"),
    ("Airtime and data bundle", "out", "airtime"),
    ("Frais scolaires trimestre 2", "out", "education"),
])
def test_categories_across_languages(description, direction, expected):
    assert doc(description, direction).category == expected


def test_salary_into_own_account_stays_salary():
    assert doc("Salary payment to my account", "in").category == "salary"


def test_gemini_category_is_kept_when_no_rule_applies():
    assert doc("Something unusual", "out", category="health").category == "health"


def test_every_line_on_a_rent_receipt_is_rent():
    t = doc("Reçu n° 12 - mars", "in", doc_type="rent_receipts")
    assert (t.direction, t.category) == ("out", "rent")
