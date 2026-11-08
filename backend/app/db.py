import json
import logging
from pathlib import Path

import asyncpg

from .config import settings

log = logging.getLogger("creditvirgin.db")

_pool: asyncpg.Pool | None = None


async def _init_conn(conn: asyncpg.Connection) -> None:
    await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")
    await conn.set_type_codec("json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=settings.timescale_service_url,
            min_size=1,
            max_size=5,
            init=_init_conn,
        )
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def _split_statements(sql: str) -> list[str]:
    out, buf = [], []
    for line in sql.splitlines():
        if line.strip().startswith("--"):
            continue
        buf.append(line)
        if line.rstrip().endswith(";"):
            stmt = "\n".join(buf).strip()
            if stmt:
                out.append(stmt.rstrip(";"))
            buf = []
    return out


async def init_schema() -> None:
    """Run schema.sql statement by statement (continuous aggregates can't run inside a transaction)."""
    sql = (Path(__file__).parent / "schema.sql").read_text()
    pool = await get_pool()
    async with pool.acquire() as conn:
        for stmt in _split_statements(sql):
            try:
                await conn.execute(stmt)
            except asyncpg.PostgresError as e:  # idempotency: tolerate already-exists errors
                msg = str(e).lower()
                if "already exists" in msg or "already a hypertable" in msg:
                    continue
                log.error("schema statement failed: %s\n%s", e, stmt[:200])
                raise
    log.info("schema ready")


async def refresh_monthly_cashflow() -> None:
    """Force the continuous aggregate to include freshly inserted rows (demo-friendly)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            await conn.execute("CALL refresh_continuous_aggregate('monthly_cashflow', NULL, NULL)")
        except asyncpg.PostgresError as e:
            log.warning("refresh_continuous_aggregate failed: %s", e)
