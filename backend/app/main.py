import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import close_pool, init_schema
from .routers import documents, marketplace, media, score, share

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_schema()
    await marketplace.seed_samples()
    warmup = asyncio.create_task(media.warm(marketplace.sample_media_files()))
    yield
    warmup.cancel()
    await close_pool()


app = FastAPI(title="Credit Virgin API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(documents.router)
app.include_router(score.router)
app.include_router(share.router)
app.include_router(marketplace.router)
app.include_router(media.router)


@app.get("/api/health")
async def health():
    return {"ok": True, "model": settings.gemini_model, "auth": bool(settings.auth0_domain)}
