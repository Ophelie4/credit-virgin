"""Sample listing photos and walkthrough videos, cached on disk so the demo keeps working without Wi-Fi.

The first request for a file (or the warm-up at startup) downloads it from the Higgsfield CDN; after that it is
served from backend/media_cache. Only file names in the CDN's own format are accepted, so this can't be used to
fetch arbitrary URLs.
"""
import asyncio
import logging
import re
import urllib.request
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..config import settings

log = logging.getLogger("creditvirgin.media")
router = APIRouter(prefix="/api/media", tags=["media"])

REMOTE = "https://d8j0ntlcm91z4.cloudfront.net/user_3JkGjNqq8OOj9gf4yMqVWNIEXF6/hf_20261108_"
NAME = re.compile(r"^\d{6}_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.(png|jpg|mp4)$")
_locks: dict[str, asyncio.Lock] = {}


def cache_dir() -> Path:
    d = Path(settings.media_cache_dir)
    if not d.is_absolute():
        d = Path(__file__).resolve().parents[2] / d
    d.mkdir(parents=True, exist_ok=True)
    return d


def _download(name: str, dest: Path) -> None:
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(REMOTE + name, headers={"User-Agent": "credit-virgin/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
        while chunk := r.read(1 << 16):
            f.write(chunk)
    tmp.replace(dest)


async def ensure(name: str) -> Path:
    if not NAME.match(name):
        raise HTTPException(404, "Unknown media")
    dest = cache_dir() / name
    if dest.exists():
        return dest
    async with _locks.setdefault(name, asyncio.Lock()):
        if not dest.exists():
            try:
                await asyncio.to_thread(_download, name, dest)
            except Exception as e:  # offline and not cached yet
                log.warning("could not fetch %s: %s", name, e)
                raise HTTPException(503, "Media not available offline yet")
    return dest


@router.get("/{name}")
async def media(name: str):
    path = await ensure(name)
    return FileResponse(path, headers={"Cache-Control": "public, max-age=31536000, immutable"})


async def warm(names: list[str]) -> None:
    """Download every sample file that isn't cached yet, a few at a time, without blocking startup."""
    missing = [n for n in names if NAME.match(n) and not (cache_dir() / n).exists()]
    if not missing:
        return
    sem = asyncio.Semaphore(4)

    async def one(n: str):
        async with sem:
            try:
                await ensure(n)
            except HTTPException:
                pass
    await asyncio.gather(*(one(n) for n in missing))
    log.info("media cache: %d/%d sample files saved", sum((cache_dir() / n).exists() for n in missing), len(missing))
