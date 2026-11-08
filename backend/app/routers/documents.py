import asyncio
import hashlib
import json
import logging
import uuid
from pathlib import Path
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..auth import ApplicantId
from ..config import settings
from ..db import get_pool, refresh_monthly_cashflow
from ..models import DocumentOut, ExtractedDocument
from ..services.gemini import extract_document
from ..services.normalize import normalize
from ..services.local_parser import parse as local_parse, pdf_text

log = logging.getLogger("creditvirgin.documents")
router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED = {"application/pdf", "image/png", "image/jpeg", "image/webp"}
MAX_BYTES = 15 * 1024 * 1024


@router.post("", response_model=DocumentOut)
async def upload_document(file: UploadFile = File(...), applicant_id: uuid.UUID = ApplicantId):
    mime = file.content_type or "application/pdf"
    if mime not in ALLOWED:
        raise HTTPException(415, f"Unsupported file type {mime}. Upload a PDF or image.")
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File too large (15 MB max).")

    cache = Path(settings.extraction_cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    cached = cache / f"{hashlib.sha256(data).hexdigest()}.json"
    if cached.exists():
        extracted = normalize(ExtractedDocument.model_validate_json(cached.read_text()))
        log.info("extraction cache hit for %s", file.filename)
    else:
        text = pdf_text(data) if mime == "application/pdf" else ""
        extracted = None
        try:
            extracted = normalize(await asyncio.wait_for(
                extract_document(data, mime, file.filename or "document", text), timeout=settings.extraction_budget_s))
            log.info("gemini extracted %s (%d rows)", file.filename, len(extracted.transactions))
        except Exception as e:  # noqa: BLE001
            log.warning("gemini extraction failed for %s: %s", file.filename, str(e)[:160])
            fallback = local_parse(text)
            if fallback is None:
                raise HTTPException(502, "Could not read this document right now. Try again in a minute, or upload a clearer scan.")
            extracted = normalize(fallback)
            log.info("local parser extracted %s (%d rows)", file.filename, len(extracted.transactions))
        cached.write_text(json.dumps(extracted.model_dump(mode="json")))

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            doc = await conn.fetchrow(
                """INSERT INTO documents (applicant_id, filename, doc_type, source_name, account_holder, currency,
                                          language, period_start, period_end, opening_balance, tx_count, raw_json)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12) RETURNING *""",
                applicant_id, file.filename, extracted.doc_type, extracted.source_name, extracted.account_holder,
                extracted.currency.upper(), extracted.language, extracted.period_start, extracted.period_end,
                extracted.opening_balance, len(extracted.transactions), extracted.model_dump(mode="json"),
            )
            # noon UTC + one second per row keeps the document's row order inside a single day
            rows = [
                (datetime(t.date.year, t.date.month, t.date.day, 12, tzinfo=timezone.utc) + timedelta(seconds=i),
                 applicant_id, doc["id"], extracted.doc_type, t.description, t.direction, t.amount, t.fee or 0,
                 t.balance, extracted.currency.upper(), t.category, t.counterparty)
                for i, t in enumerate(extracted.transactions)
            ]
            await conn.executemany(
                """INSERT INTO transactions (time, applicant_id, document_id, doc_type, description, direction, amount,
                                             fee, balance, currency, category, counterparty)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)""",
                rows,
            )
    await refresh_monthly_cashflow()
    return _to_out(doc)


@router.get("", response_model=list[DocumentOut])
async def list_documents(applicant_id: uuid.UUID = ApplicantId):
    pool = await get_pool()
    rows = await pool.fetch("SELECT * FROM documents WHERE applicant_id=$1 ORDER BY created_at", applicant_id)
    return [_to_out(r) for r in rows]


@router.delete("/{doc_id}")
async def delete_document(doc_id: uuid.UUID, applicant_id: uuid.UUID = ApplicantId):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("DELETE FROM transactions WHERE document_id=$1 AND applicant_id=$2", doc_id, applicant_id)
            res = await conn.execute("DELETE FROM documents WHERE id=$1 AND applicant_id=$2", doc_id, applicant_id)
    if res.endswith("0"):
        raise HTTPException(404, "Document not found")
    await refresh_monthly_cashflow()
    return {"ok": True}


@router.delete("")
async def reset_all(applicant_id: uuid.UUID = ApplicantId):
    """Demo helper: wipe this applicant's documents and transactions."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("DELETE FROM transactions WHERE applicant_id=$1", applicant_id)
            await conn.execute("DELETE FROM documents WHERE applicant_id=$1", applicant_id)
            await conn.execute("DELETE FROM applications WHERE renter_id=$1", applicant_id)
    await refresh_monthly_cashflow()
    return {"ok": True}


@router.get("/{doc_id}/transactions")
async def document_transactions(doc_id: uuid.UUID, applicant_id: uuid.UUID = ApplicantId):
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT time::date AS date, description, direction, amount, fee, balance, category, counterparty
           FROM transactions WHERE document_id=$1 AND applicant_id=$2 ORDER BY time, id""", doc_id, applicant_id)
    return [dict(r) for r in rows]


def _to_out(r) -> DocumentOut:
    return DocumentOut(
        id=str(r["id"]), filename=r["filename"], doc_type=r["doc_type"], source_name=r["source_name"],
        currency=r["currency"], language=r["language"], period_start=r["period_start"], period_end=r["period_end"],
        tx_count=r["tx_count"], created_at=r["created_at"].isoformat(),
    )
