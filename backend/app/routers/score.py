import logging
import uuid

from fastapi import APIRouter, Query

from ..auth import ApplicantId
from ..config import settings
from ..db import get_pool
from ..models import ScoreOut
from ..services import verification
from ..services.gemini import explain_score
from ..services.scoring import band_for, compute_factors, summarize_payments

log = logging.getLogger("creditvirgin.score")
router = APIRouter(prefix="/api", tags=["score"])


async def build_score(applicant_id: uuid.UUID, language: str, audience: str, with_explanation: bool = True) -> ScoreOut:
    pool = await get_pool()
    async with pool.acquire() as conn:
        months = [dict(r) for r in await conn.fetch(
            "SELECT * FROM monthly_cashflow WHERE applicant_id=$1 ORDER BY month", applicant_id)]
        txs = [dict(r) for r in await conn.fetch(
            "SELECT * FROM transactions WHERE applicant_id=$1 ORDER BY time, id", applicant_id)]
        docs = {str(r["id"]): dict(r) for r in await conn.fetch(
            "SELECT id, doc_type, opening_balance, currency FROM documents WHERE applicant_id=$1", applicant_id)}

    tx_summary = summarize_payments(txs)
    score, factors = compute_factors(months, tx_summary)
    checks = verification.run_all(txs, docs) if txs else []

    # Any failed verification caps the score: evidence that doesn't agree isn't evidence.
    if any(c.status == "fail" for c in checks):
        score = min(score, 45)

    currency = next((d["currency"] for d in docs.values() if d.get("currency")), None)
    inflows = [float(m["inflow"] or 0) for m in months if m["inflow"]]
    rents = [float(m["rent_paid"]) for m in months if m["rent_paid"]]
    avg_income = sum(inflows) / len(inflows) if inflows else None
    avg_rent = sum(rents) / len(rents) if rents else None
    fx = settings.fx_table.get((currency or "").upper())
    avg_income_usd = (avg_income / fx) if (avg_income and fx) else None

    out = ScoreOut(
        score=score, band=band_for(score), factors=factors, checks=checks, months_covered=len(months),
        currency=currency, avg_monthly_income=avg_income, avg_monthly_income_usd=avg_income_usd, avg_rent=avg_rent,
        rent_to_income=(avg_rent / avg_income) if (avg_rent and avg_income) else None,
        on_time_rent_months=tx_summary["rent_months_paid"],
    )
    if with_explanation and txs:
        summary = {
            "score": score, "band": out.band, "months_covered": len(months), "currency": currency,
            "avg_monthly_income": round(avg_income) if avg_income else None,
            "avg_monthly_income_usd": round(avg_income_usd) if avg_income_usd else None,
            "rent_months_paid": tx_summary["rent_months_paid"], "rent_months_expected": tx_summary["rent_months_expected"],
            "factors": [{"label": f.label, "points": f.points, "max": f.max_points, "detail": f.detail} for f in factors],
            "checks": [{"label": c.label, "status": c.status} for c in checks],
        }
        failed = [{"label": c.label, "detail": c.detail} for c in checks if c.status == "fail"]
        if failed:  # only added when something failed, so explanations already cached for clean files stay valid
            summary["failed_checks"] = failed
            summary["score_capped_at"] = 45
        out.explanation = await explain_score(summary, language, audience)
    return out


@router.get("/score", response_model=ScoreOut)
async def get_score(lang: str = Query("en"), explain: bool = Query(True), applicant_id: uuid.UUID = ApplicantId):
    return await build_score(applicant_id, lang, "applicant", with_explanation=explain)


@router.get("/cashflow")
async def get_cashflow(applicant_id: uuid.UUID = ApplicantId):
    """Monthly series for charts, straight from the Tiger Data continuous aggregate."""
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT to_char(month, 'YYYY-MM') AS month, inflow, outflow, rent_paid, saved, salary, tx_count, min_balance
           FROM monthly_cashflow WHERE applicant_id=$1 ORDER BY month""", applicant_id)
    bal = await pool.fetch(
        """WITH best AS (
             SELECT document_id FROM transactions WHERE applicant_id=$1 AND balance IS NOT NULL
             GROUP BY document_id ORDER BY count(*) DESC LIMIT 1)
           SELECT time::date AS date, balance, doc_type FROM transactions
           WHERE applicant_id=$1 AND balance IS NOT NULL AND document_id = (SELECT document_id FROM best)
           ORDER BY time, id""", applicant_id)
    cats = await pool.fetch(
        """SELECT category, SUM(amount) AS total, COUNT(*) AS n FROM transactions
           WHERE applicant_id=$1 AND direction='out' AND doc_type <> 'rent_receipts'
           GROUP BY category ORDER BY total DESC""", applicant_id)
    return {
        "months": [dict(r) for r in rows],
        "balances": [dict(r) for r in bal],
        "categories": [dict(r) for r in cats],
    }
