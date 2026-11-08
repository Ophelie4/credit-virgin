"""Auth0 JWT verification. When AUTH0_DOMAIN is unset, everyone is the shared demo applicant."""
import logging
import uuid

import jwt
from fastapi import Depends, Header, HTTPException
from jwt import PyJWKClient

from .config import settings
from .db import get_pool

log = logging.getLogger("creditvirgin.auth")

_jwks: PyJWKClient | None = None
DEMO_SUB = "demo|credit-virgin"          # demo renter (also owns the sample documents)
DEMO_LANDLORD_SUB = "demo|landlord"       # owns the sample listings


def _jwks_client() -> PyJWKClient:
    global _jwks
    if _jwks is None:
        _jwks = PyJWKClient(f"https://{settings.auth0_domain}/.well-known/jwks.json", cache_keys=True)
    return _jwks


def _verify(token: str) -> dict:
    key = _jwks_client().get_signing_key_from_jwt(token).key
    return jwt.decode(
        token, key, algorithms=["RS256"],
        audience=settings.auth0_audience,
        issuer=f"https://{settings.auth0_domain}/",
    )


async def _upsert_applicant(sub: str, name: str | None, email: str | None) -> uuid.UUID:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO applicants (auth0_sub, display_name, email) VALUES ($1, $2, $3)
               ON CONFLICT (auth0_sub) DO UPDATE SET display_name = COALESCE(EXCLUDED.display_name, applicants.display_name),
                                                     email = COALESCE(EXCLUDED.email, applicants.email)
               RETURNING id""",
            sub, name, email,
        )
        return row["id"]


async def current_applicant(authorization: str | None = Header(default=None),
                            x_demo_role: str | None = Header(default=None)) -> uuid.UUID:
    """FastAPI dependency returning the user's UUID for this request.

    Without Auth0 configured, the app runs in demo mode: the X-Demo-Role header picks the demo renter or the
    demo landlord, so both sides can be shown on one machine.
    """
    if not settings.auth0_domain or (authorization is None and x_demo_role):
        if x_demo_role == "landlord":
            uid = await _upsert_applicant(DEMO_LANDLORD_SUB, "Harbor & Pine Homes", None)
            await _set_role(uid, "landlord")
            return uid
        uid = await _upsert_applicant(DEMO_SUB, "Aline Uwase", None)
        await _set_role(uid, "renter", only_if_empty=True)
        return uid

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        claims = _verify(token)
    except Exception as e:
        log.info("token rejected: %s", e)
        raise HTTPException(status_code=401, detail="Invalid token")
    return await _upsert_applicant(claims["sub"], claims.get("name"), claims.get("email"))


async def _set_role(uid: uuid.UUID, role: str, only_if_empty: bool = False) -> None:
    pool = await get_pool()
    q = "UPDATE applicants SET role=$2 WHERE id=$1" + (" AND role IS NULL" if only_if_empty else "")
    await pool.execute(q, uid, role)


async def get_role(uid: uuid.UUID) -> str | None:
    pool = await get_pool()
    return await pool.fetchval("SELECT role FROM applicants WHERE id=$1", uid)


def require_role(role: str):
    async def _dep(uid: uuid.UUID = Depends(current_applicant)) -> uuid.UUID:
        if await get_role(uid) != role:
            raise HTTPException(status_code=403, detail=f"This page is for {role}s.")
        return uid
    return _dep


ApplicantId = Depends(current_applicant)
LandlordId = Depends(require_role("landlord"))
RenterId = Depends(require_role("renter"))
