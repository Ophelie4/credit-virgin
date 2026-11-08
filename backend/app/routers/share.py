import secrets
import uuid

from fastapi import APIRouter, HTTPException, Query, Request

from ..auth import ApplicantId
from ..config import settings
from ..db import get_pool
from .score import build_score

router = APIRouter(prefix="/api", tags=["share"])


@router.post("/share")
async def create_share_link(request: Request, label: str = Query("Landlord"), applicant_id: uuid.UUID = ApplicantId):
    token = secrets.token_urlsafe(8)
    pool = await get_pool()
    await pool.execute("INSERT INTO share_links (token, applicant_id, label) VALUES ($1,$2,$3)", token, applicant_id, label)
    return {"token": token, "url": f"{_base(request)}/r/{token}"}


def _base(request: Request) -> str:
    """Prefer the page that made the request (works on any dev port), else the configured base URL."""
    origin = request.headers.get("origin") or ""
    return (origin or settings.app_base_url).rstrip("/")


@router.get("/share")
async def list_share_links(request: Request, applicant_id: uuid.UUID = ApplicantId):
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT token, label, created_at, expires_at, views FROM share_links WHERE applicant_id=$1 ORDER BY created_at DESC",
        applicant_id)
    base = _base(request)
    return [{**dict(r), "url": f"{base}/r/{r['token']}"} for r in rows]


@router.get("/report/{token}")
async def public_report(token: str, lang: str = Query("en")):
    """Public, read-only report for a landlord or lender. No login required."""
    pool = await get_pool()
    link = await pool.fetchrow(
        "SELECT s.*, a.display_name FROM share_links s JOIN applicants a ON a.id=s.applicant_id WHERE token=$1 AND expires_at > now()",
        token)
    if not link:
        raise HTTPException(404, "This link has expired or does not exist.")
    await pool.execute("UPDATE share_links SET views = views + 1 WHERE token=$1", token)
    score = await build_score(link["applicant_id"], lang, "landlord")
    docs = await pool.fetch(
        "SELECT doc_type, source_name, period_start, period_end, tx_count FROM documents WHERE applicant_id=$1 ORDER BY period_start",
        link["applicant_id"])
    return {
        "applicant_name": link["display_name"] or "Applicant",
        "generated_for": link["label"],
        "views": link["views"] + 1,
        "documents": [dict(d) for d in docs],
        "score": score.model_dump(),
    }
