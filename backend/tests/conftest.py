"""Shared test setup. Settings need these two values to import; tests never touch the database or Gemini."""
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

os.environ.setdefault("TIMESCALE_SERVICE_URL", "postgres://test:test@localhost:5432/test")
os.environ.setdefault("GEMINI_API_KEY", "test")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

SAMPLES = Path(__file__).resolve().parents[2] / "samples"


def to_rows(docs):
    """Turn ExtractedDocuments into transaction rows the way the upload endpoint stores them."""
    rows, meta, rid = [], {}, 0
    for n, doc in enumerate(docs):
        doc_id = f"doc{n}"
        meta[doc_id] = {"doc_type": doc.doc_type, "opening_balance": doc.opening_balance, "currency": doc.currency}
        for i, t in enumerate(doc.transactions):
            rid += 1
            rows.append({
                "id": rid, "document_id": doc_id, "doc_type": doc.doc_type,
                "time": datetime(t.date.year, t.date.month, t.date.day, 12, tzinfo=timezone.utc) + timedelta(seconds=i),
                "description": t.description, "direction": t.direction, "amount": t.amount, "fee": t.fee or 0,
                "balance": t.balance, "category": t.category, "counterparty": t.counterparty,
            })
    rows.sort(key=lambda r: (r["time"], r["id"]))
    return rows, meta


def monthly(rows):
    """Same numbers as the monthly_cashflow continuous aggregate in schema.sql."""
    out = defaultdict(lambda: {"inflow": 0.0, "outflow": 0.0, "rent_paid": 0.0, "saved": 0.0, "salary": 0.0})
    for r in rows:
        if r["doc_type"] == "rent_receipts" or r["category"] in ("transfer_in", "transfer_out"):
            continue
        m = out[(r["time"].year, r["time"].month)]
        if r["direction"] == "in":
            m["inflow"] += r["amount"]
            if r["category"] == "salary":
                m["salary"] += r["amount"]
        else:
            m["outflow"] += r["amount"]
            if r["category"] == "rent":
                m["rent_paid"] += r["amount"]
            if r["category"] == "savings":
                m["saved"] += r["amount"]
    return [out[k] for k in sorted(out)]


@pytest.fixture
def sample_doc():
    """Read one of the sample PDFs with the offline parser and the category guardrails."""
    from app.services.local_parser import parse, pdf_text
    from app.services.normalize import normalize

    def load(name):
        doc = parse(pdf_text((SAMPLES / name).read_bytes()))
        assert doc is not None, f"could not parse {name}"
        return normalize(doc)
    return load
