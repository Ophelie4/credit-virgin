"""Two-sided marketplace: landlords list homes with their own requirements, renters see where they stand and apply
by sending their verified report. Applicant-controlled: a landlord only sees a report the renter chose to send."""
import datetime as dt
import logging
import secrets
import uuid

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..auth import DEMO_LANDLORD_SUB, ApplicantId, LandlordId, RenterId, get_role, _upsert_applicant, _set_role
from ..config import settings
from ..db import get_pool
from .score import build_score

log = logging.getLogger("creditvirgin.marketplace")
router = APIRouter(prefix="/api", tags=["marketplace"])


# ---------------------------------------------------------------- accounts
class MeIn(BaseModel):
    role: str | None = Field(default=None, pattern="^(renter|landlord)$")
    us_monthly_income: float | None = Field(default=None, ge=0)
    display_name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=254)


@router.get("/me")
async def get_me(uid: uuid.UUID = ApplicantId):
    pool = await get_pool()
    r = await pool.fetchrow("SELECT id, role, display_name, email, us_monthly_income FROM applicants WHERE id=$1", uid)
    return {**dict(r), "id": str(r["id"]), "us_monthly_income": float(r["us_monthly_income"]) if r["us_monthly_income"] else None}


@router.post("/me")
async def update_me(body: MeIn, uid: uuid.UUID = ApplicantId):
    pool = await get_pool()
    if body.role:
        await pool.execute("UPDATE applicants SET role=$2 WHERE id=$1", uid, body.role)
    if body.us_monthly_income is not None:
        await pool.execute("UPDATE applicants SET us_monthly_income=$2 WHERE id=$1", uid, body.us_monthly_income)
    if body.display_name:
        await pool.execute("UPDATE applicants SET display_name=$2 WHERE id=$1", uid, body.display_name)
    if body.email:
        await pool.execute("UPDATE applicants SET email=$2 WHERE id=$1", uid, body.email)
    return await get_me(uid)


# ---------------------------------------------------------------- listings (landlord)
class PropertyIn(BaseModel):
    title: str
    property_type: str | None = "apartment"
    neighborhood: str | None = None
    city: str | None = "Miami"
    lat: float | None = None
    lng: float | None = None
    monthly_rent: float = Field(gt=0)
    security_deposit: float | None = None
    first_last_required: bool = False
    application_fee: float | None = None
    bedrooms: int | None = None
    bathrooms: float | None = None
    size_sqft: int | None = None
    lease_months: int | None = 12
    available_from: dt.date | None = None
    furnished: bool = False
    pets_allowed: bool = False
    parking: bool = False
    utilities_included: list[str] = []
    amenities: list[str] = []
    description: str | None = None
    palette: int = 0
    photo_urls: list[str] = []
    tour_url: str | None = None
    min_score: int = Field(default=50, ge=0, le=100)
    max_rent_to_income: float = Field(default=0.40, gt=0, le=1)
    status: str = "listed"


FIELDS = list(PropertyIn.model_fields.keys())

# approximate neighborhood centres, used when a landlord doesn't give coordinates
NEIGHBORHOODS = {
    "little havana": (25.7654, -80.2195), "wynwood": (25.8010, -80.1994), "brickell": (25.7617, -80.1918),
    "coconut grove": (25.7280, -80.2420), "miami shores": (25.8631, -80.1928), "little haiti": (25.8305, -80.1955),
    "edgewater": (25.8010, -80.1880), "north miami": (25.8901, -80.1867), "coral gables": (25.7215, -80.2684),
    "doral": (25.8195, -80.3553), "allapattah": (25.8150, -80.2240), "downtown": (25.7743, -80.1937),
}


def _coords(p: PropertyIn) -> tuple[float | None, float | None]:
    if p.lat and p.lng:
        return p.lat, p.lng
    return NEIGHBORHOODS.get((p.neighborhood or "").strip().lower(), (25.7743, -80.1937))


def _row(r) -> dict:
    d = dict(r)
    d["id"] = str(d["id"])
    d["landlord_id"] = str(d["landlord_id"])
    for k in ("monthly_rent", "security_deposit", "application_fee", "bathrooms", "max_rent_to_income"):
        if d.get(k) is not None:
            d[k] = float(d[k])
    d["move_in_cost"] = d["monthly_rent"] * (2 if d.get("first_last_required") else 1) + (d.get("security_deposit") or 0) \
        + (d.get("application_fee") or 0)
    return d


@router.post("/properties")
async def create_property(body: PropertyIn, uid: uuid.UUID = LandlordId):
    lat, lng = _coords(body)
    vals = body.model_dump()
    vals.update(lat=lat, lng=lng)
    cols = ", ".join(FIELDS)
    ph = ", ".join(f"${i + 2}" for i in range(len(FIELDS)))
    pool = await get_pool()
    r = await pool.fetchrow(f"INSERT INTO properties (landlord_id, {cols}) VALUES ($1, {ph}) RETURNING *",
                            uid, *[vals[f] for f in FIELDS])
    return _row(r)


@router.patch("/properties/{pid}")
async def update_property(pid: uuid.UUID, body: PropertyIn, uid: uuid.UUID = LandlordId):
    lat, lng = _coords(body)
    vals = body.model_dump()
    vals.update(lat=lat, lng=lng)
    sets = ", ".join(f"{f}=${i + 3}" for i, f in enumerate(FIELDS))
    pool = await get_pool()
    r = await pool.fetchrow(f"UPDATE properties SET {sets} WHERE id=$1 AND landlord_id=$2 RETURNING *",
                            pid, uid, *[vals[f] for f in FIELDS])
    if not r:
        raise HTTPException(404, "Listing not found")
    return _row(r)


@router.delete("/properties/{pid}")
async def delete_property(pid: uuid.UUID, uid: uuid.UUID = LandlordId):
    pool = await get_pool()
    await pool.execute("DELETE FROM properties WHERE id=$1 AND landlord_id=$2", pid, uid)
    return {"ok": True}


@router.get("/properties/mine")
async def my_properties(uid: uuid.UUID = LandlordId):
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT p.*, (SELECT count(*) FROM applications a WHERE a.property_id=p.id) AS application_count,
                  (SELECT count(*) FROM applications a WHERE a.property_id=p.id AND a.status='pending') AS pending_count
           FROM properties p WHERE landlord_id=$1 ORDER BY monthly_rent""", uid)
    return [_row(r) for r in rows]


@router.post("/properties/load-samples")
async def load_sample_portfolio(uid: uuid.UUID = LandlordId):
    """Give this landlord a copy of the six sample listings (for a fresh account on demo day)."""
    pool = await get_pool()
    n = await pool.fetchval("SELECT count(*) FROM properties WHERE landlord_id=$1", uid)
    if n:
        return {"ok": True, "created": 0}
    for s in SAMPLE_LISTINGS:
        await create_property(PropertyIn(**s), uid)
    return {"ok": True, "created": len(SAMPLE_LISTINGS)}


# ---------------------------------------------------------------- matching (renter)
TIPS = {
    "savings": "Set aside a fixed amount every month, even small. Savings-group (ikimina, tontine, chama) transfers count.",
    "history": "Add older statements. Twelve months of history earns the full points.",
    "income_stability": "Upload payslips or an offer letter so steady income is easy to see.",
    "payment_consistency": "Add rent receipts or utility bills that show on-time payments.",
    "balance_health": "Keep a small cushion so the balance never dips below zero, and spend less than you earn each month.",
}


def _weakest_tip(score) -> dict | None:
    if not score.factors:
        return None
    f = min(score.factors, key=lambda f: f.points / f.max_points)
    if f.points >= f.max_points:
        return None
    return {"factor": f.key, "label": f.label, "points": f.points, "max_points": f.max_points,
            "tip": TIPS.get(f.key, "Add more documents.")}


def classify(p: dict, score: int, us_income: float | None) -> tuple[str, str | None]:
    if us_income:
        needed = p["monthly_rent"] / p["max_rent_to_income"]
        if us_income < needed:
            return "not_yet", f"Needs about ${needed:,.0f} a month in income (yours: ${us_income:,.0f})."
    if score >= p["min_score"]:
        return "within_reach", None
    return "almost", f"Raise your score by {p['min_score'] - score} to qualify."


@router.get("/homes")
async def homes(uid: uuid.UUID = RenterId):
    pool = await get_pool()
    me = await pool.fetchrow("SELECT us_monthly_income FROM applicants WHERE id=$1", uid)
    income = float(me["us_monthly_income"]) if me["us_monthly_income"] else None
    s = await build_score(uid, "en", "applicant", with_explanation=False)
    has_score = s.months_covered > 0
    rows = await pool.fetch(
        """SELECT p.*, a.display_name AS landlord_name, ap.status AS my_application
           FROM properties p JOIN applicants a ON a.id = p.landlord_id
           LEFT JOIN applications ap ON ap.property_id = p.id AND ap.renter_id = $1
           WHERE p.status = 'listed' ORDER BY p.monthly_rent""", uid)
    out = []
    for r in rows:
        d = _row(r)
        if has_score:
            d["match"], d["gap"] = classify(d, s.score, income)
        else:
            d["match"], d["gap"] = "no_score", "Upload your documents to see if you qualify."
        out.append(d)
    return {
        "score": s.score if has_score else None, "band": s.band if has_score else None,
        "us_monthly_income": income, "tip": _weakest_tip(s) if has_score else None, "homes": out,
    }


@router.get("/homes/{pid}")
async def home_detail(pid: uuid.UUID, uid: uuid.UUID = ApplicantId):
    pool = await get_pool()
    r = await pool.fetchrow(
        """SELECT p.*, a.display_name AS landlord_name, a.email AS landlord_email, ap.status AS my_application,
                  ap.landlord_note AS my_application_note
           FROM properties p JOIN applicants a ON a.id = p.landlord_id
           LEFT JOIN applications ap ON ap.property_id = p.id AND ap.renter_id = $2
           WHERE p.id = $1""", pid, uid)
    if not r:
        raise HTTPException(404, "Listing not found")
    d = _row(r)
    if await get_role(uid) == "renter":
        me = await pool.fetchrow("SELECT us_monthly_income FROM applicants WHERE id=$1", uid)
        income = float(me["us_monthly_income"]) if me["us_monthly_income"] else None
        s = await build_score(uid, "en", "applicant", with_explanation=False)
        if s.months_covered:
            d["match"], d["gap"] = classify(d, s.score, income)
            d["score"] = s.score
            d["tip"] = _weakest_tip(s)
        else:
            d["match"], d["gap"], d["score"] = "no_score", "Upload your documents to see if you qualify.", None
    return d


class ApplyIn(BaseModel):
    message: str | None = Field(default=None, max_length=1000)


@router.post("/homes/{pid}/apply")
async def apply(pid: uuid.UUID, body: ApplyIn, request: Request, uid: uuid.UUID = RenterId):
    pool = await get_pool()
    p = await pool.fetchrow("SELECT * FROM properties WHERE id=$1 AND status='listed'", pid)
    if not p:
        raise HTTPException(404, "Listing not found")
    s = await build_score(uid, "en", "applicant", with_explanation=False)
    if not s.months_covered:
        raise HTTPException(400, "Upload your documents first so there is a report to send.")
    token = secrets.token_urlsafe(8)
    await pool.execute("INSERT INTO share_links (token, applicant_id, label) VALUES ($1,$2,$3)", token, uid, p["title"])
    r = await pool.fetchrow(
        """INSERT INTO applications (property_id, renter_id, share_token, score_at_submit, message)
           VALUES ($1,$2,$3,$4,$5)
           ON CONFLICT (property_id, renter_id) DO UPDATE
             SET share_token=EXCLUDED.share_token, score_at_submit=EXCLUDED.score_at_submit, message=EXCLUDED.message,
                 status='pending', landlord_note=NULL, decided_at=NULL, created_at=now()
           RETURNING id""", pid, uid, token, s.score, body.message)
    return {"ok": True, "application_id": str(r["id"]), "score": s.score}


@router.get("/applications/mine")
async def my_applications(uid: uuid.UUID = RenterId):
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT ap.id, ap.status, ap.score_at_submit, ap.landlord_note, ap.created_at, ap.decided_at,
                  p.id AS property_id, p.title, p.neighborhood, p.monthly_rent, p.palette, p.photo_urls, a.display_name AS landlord_name
           FROM applications ap JOIN properties p ON p.id = ap.property_id JOIN applicants a ON a.id = p.landlord_id
           WHERE ap.renter_id=$1 ORDER BY ap.created_at DESC""", uid)
    return [{**dict(r), "id": str(r["id"]), "property_id": str(r["property_id"]), "monthly_rent": float(r["monthly_rent"])}
            for r in rows]


# ---------------------------------------------------------------- inbox (landlord)
@router.get("/landlord/applications")
async def landlord_inbox(request: Request, uid: uuid.UUID = LandlordId):
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT ap.id, ap.status, ap.score_at_submit, ap.message, ap.landlord_note, ap.share_token, ap.created_at,
                  ap.decided_at, p.id AS property_id, p.title, p.monthly_rent, p.min_score,
                  r.display_name AS renter_name, r.us_monthly_income
           FROM applications ap JOIN properties p ON p.id = ap.property_id JOIN applicants r ON r.id = ap.renter_id
           WHERE p.landlord_id=$1 ORDER BY (ap.status='pending') DESC, ap.created_at DESC""", uid)
    base = (request.headers.get("origin") or settings.app_base_url).rstrip("/")
    return [{**dict(r), "id": str(r["id"]), "property_id": str(r["property_id"]),
             "monthly_rent": float(r["monthly_rent"]),
             "us_monthly_income": float(r["us_monthly_income"]) if r["us_monthly_income"] else None,
             "report_url": f"{base}/r/{r['share_token']}" if r["share_token"] else None} for r in rows]


class DecisionIn(BaseModel):
    status: str = Field(pattern="^(approved|declined)$")
    note: str | None = Field(default=None, max_length=1000)


@router.post("/applications/{aid}/decision")
async def decide(aid: uuid.UUID, body: DecisionIn, uid: uuid.UUID = LandlordId):
    pool = await get_pool()
    r = await pool.fetchrow(
        """UPDATE applications ap SET status=$3, landlord_note=$4, decided_at=now()
           FROM properties p WHERE ap.id=$1 AND p.id=ap.property_id AND p.landlord_id=$2 RETURNING ap.id""",
        aid, uid, body.status, body.note)
    if not r:
        raise HTTPException(404, "Application not found")
    return {"ok": True}


# ---------------------------------------------------------------- sample portfolio (fictional)
SAMPLE_LISTINGS = [
    dict(title="Sunny studio near Calle Ocho", property_type="studio", neighborhood="Little Havana", monthly_rent=1150,
         security_deposit=1150, application_fee=50, bedrooms=0, bathrooms=1, size_sqft=420, lease_months=12,
         utilities_included=["water", "trash"], amenities=["AC", "Shared laundry", "Near Metrobus"], palette=0,
         min_score=40, max_rent_to_income=0.40,
         description="Bright studio two blocks from Calle Ocho. Ideal for a student or first job in the city."),
    dict(title="Garden 1-bed by Miami Shores park", property_type="apartment", neighborhood="Miami Shores",
         monthly_rent=1450, security_deposit=1450, application_fee=50, bedrooms=1, bathrooms=1, size_sqft=640,
         lease_months=12, pets_allowed=True, parking=True, utilities_included=["water"],
         amenities=["AC", "In-unit laundry", "Patio"], palette=1, min_score=50, max_rent_to_income=0.40,
         description="Quiet one-bedroom with a small patio, a short walk from the park and the Biscayne bus line."),
    dict(title="Loft-style 1-bed in Wynwood", property_type="apartment", neighborhood="Wynwood", monthly_rent=1900,
         security_deposit=1900, application_fee=75, first_last_required=True, bedrooms=1, bathrooms=1, size_sqft=720,
         lease_months=12, furnished=True, amenities=["AC", "Gym", "Rooftop", "In-unit laundry"], palette=2,
         min_score=60, max_rent_to_income=0.38,
         description="Furnished loft with high ceilings in the arts district. Gym and rooftop included."),
    dict(title="Bayview 2-bed in Brickell", property_type="apartment", neighborhood="Brickell", monthly_rent=2800,
         security_deposit=2800, application_fee=100, first_last_required=True, bedrooms=2, bathrooms=2, size_sqft=1050,
         lease_months=12, parking=True, amenities=["AC", "Pool", "Gym", "Doorman", "Balcony"], palette=3,
         min_score=70, max_rent_to_income=0.35,
         description="Two bedrooms with a bay view balcony, pool and 24-hour front desk."),
    dict(title="Townhouse in Coconut Grove", property_type="house", neighborhood="Coconut Grove", monthly_rent=3600,
         security_deposit=3600, application_fee=100, first_last_required=True, bedrooms=3, bathrooms=2.5,
         size_sqft=1600, lease_months=12, pets_allowed=True, parking=True,
         amenities=["AC", "Private yard", "Garage", "In-unit laundry"], palette=4, min_score=80, max_rent_to_income=0.33,
         description="Three-level townhouse under the banyan trees, with a private yard and garage."),
    dict(title="Family house in Coral Gables", property_type="house", neighborhood="Coral Gables", monthly_rent=4500,
         security_deposit=4500, application_fee=150, first_last_required=True, bedrooms=3, bathrooms=3, size_sqft=2100,
         lease_months=24, pets_allowed=True, parking=True,
         amenities=["AC", "Pool", "Garden", "Two-car garage"], palette=5, min_score=85, max_rent_to_income=0.33,
         description="Mediterranean-style home on a quiet street, with a pool and garden."),
]


# Sample photos and walkthroughs are served through /api/media, which keeps a local copy so the demo works offline.
CDN = "/api/media/"
SAMPLE_MEDIA: dict[str, dict] = {
    "Sunny studio near Calle Ocho": {"photo_urls": [CDN + "051351_9761b3ec-6de7-4157-9f04-64eeaa16fe9e.png",
        CDN + "051429_0116bdd1-a019-4518-88af-e115b576bfd3.png", CDN + "051429_1cbb21fe-62c1-4bb8-9162-adc0ad5000a2.png"],
        "tour_url": CDN + "051819_f53e885f-6501-499b-8821-99df2c9f288b.mp4"},
    "Garden 1-bed by Miami Shores park": {"photo_urls": [CDN + "051351_23e5f96d-8e1e-4bd9-a9a7-f310945167b0.png",
        CDN + "051352_06996dee-c227-4bd2-882e-28e7ce743cef.png", CDN + "051351_5de9018e-b6ac-459e-bbf0-ae7a6d624e1d.png"],
        "tour_url": CDN + "051819_b33b091f-b1f1-4ad4-8f64-e4bc7b37fbd9.mp4"},
    "Loft-style 1-bed in Wynwood": {"photo_urls": [CDN + "051352_475ec56b-8b9e-470d-919c-9257a5d9316e.png",
        CDN + "051429_a9d3ca8e-20b0-4938-b827-0770f6a94419.png", CDN + "051502_25637256-979d-4734-85ad-b9b0ff517e7e.png"],
        "tour_url": CDN + "051820_dd29e6e9-e2fa-421d-b058-fa1ba21e8a5d.mp4"},
    "Bayview 2-bed in Brickell": {"photo_urls": [CDN + "051148_4ab285e1-5587-4da2-bd93-156f9407294f.png",
        CDN + "051148_b6793660-5d34-4a19-8eed-97943e2da86c.png", CDN + "051149_f46995c8-600a-4698-9433-836537c1d1a7.png"],
        "tour_url": CDN + "051317_26ee18fe-31cc-43fa-91d4-5c0115e89311.mp4"},
    "Townhouse in Coconut Grove": {"photo_urls": [CDN + "051351_c2e3f204-9660-4ecc-a9e1-38e76aaf9fd5.png",
        CDN + "051351_e04d3686-f13e-4a18-af87-eefd6254bd7a.png", CDN + "051351_3a071e17-7df8-4e51-b005-799a60647fb9.png"],
        "tour_url": CDN + "051819_ec4b7418-c7de-4950-a408-ac093d1ebf3a.mp4"},
    "Family house in Coral Gables": {"photo_urls": [CDN + "051500_b91166dd-3c50-4cc2-b9ba-271929183c98.png",
        CDN + "051527_d02b2c91-d96c-40dc-ba7d-c5aad0348d04.png", CDN + "051527_aebdcf7a-faf6-46a7-8d11-b530a6f861c7.png"],
        "tour_url": CDN + "051819_10da9024-2c4a-425e-8465-de81cb3df833.mp4"},
}
for _s in SAMPLE_LISTINGS:
    _s.update(SAMPLE_MEDIA.get(_s["title"], {}))


def sample_media_files() -> list[str]:
    """File names of every sample photo and walkthrough, for the offline cache."""
    urls = [u for m in SAMPLE_MEDIA.values() for u in [*m.get("photo_urls", []), m.get("tour_url")] if u]
    return [u.removeprefix(CDN) for u in urls]


async def attach_sample_media() -> None:
    """Keep sample listings' photos and walkthroughs up to date (also for copies made with load-samples)."""
    pool = await get_pool()
    for title, m in SAMPLE_MEDIA.items():
        await pool.execute("UPDATE properties SET photo_urls=$2, tour_url=COALESCE($3, tour_url) WHERE title=$1",
                           title, m.get("photo_urls", []), m.get("tour_url"))


async def seed_samples() -> None:
    """On first start, give the demo landlord the sample portfolio."""
    pool = await get_pool()
    if await pool.fetchval("SELECT count(*) FROM properties"):
        await attach_sample_media()
        return
    uid = await _upsert_applicant(DEMO_LANDLORD_SUB, "Harbor & Pine Homes", "leasing@harborandpine.example")
    await _set_role(uid, "landlord")
    for s in SAMPLE_LISTINGS:
        await create_property(PropertyIn(**s), uid)
    log.info("seeded %d sample listings", len(SAMPLE_LISTINGS))
