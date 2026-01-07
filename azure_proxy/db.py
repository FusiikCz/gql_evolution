# db.py
# Refactored to use main DB models from src/DBDefinitions/
from __future__ import annotations
import os
import json
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator, Optional, Iterable, Literal
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Import main DB models and utilities
from src.DBDefinitions import (
    BaseModel,
    ApiKeyModel,
    UsageModel,
    UserModel,
    ComposeConnectionString,
    startEngine,
)
from src.Utils.api_key_utils import hash_token, generate_api_key, verify_token

# Import API_KEY_PREFIX_LEN from utils for compatibility
from src.Utils.api_key_utils import API_KEY_PREFIX_LEN

# ---------- DB engine ----------
# Use main DB connection string, but allow override via DATABASE_URL for backward compatibility
DATABASE_URL = os.getenv("DATABASE_URL")
_async_session_maker = None
_engine = None

# Initialize immediately if DATABASE_URL is set (for backward compatibility)
if DATABASE_URL:
    from sqlalchemy.ext.asyncio import create_async_engine
    _engine = create_async_engine(DATABASE_URL, future=True, echo=False)
    AsyncSessionMaker = async_sessionmaker(_engine, expire_on_commit=False)
else:
    # Use main DB connection - will be initialized lazily
    # Create a wrapper that initializes on first use
    class LazyAsyncSessionMaker:
        def __init__(self):
            self._maker = None
        
        async def _ensure_initialized(self):
            if self._maker is None:
                connection_string = ComposeConnectionString()
                self._maker = await startEngine(connection_string, makeDrop=False, makeUp=True)
            return self._maker
        
        def __call__(self):
            if self._maker is None:
                # Try to initialize synchronously if possible (for backward compatibility)
                # This will fail if not initialized, but that's expected
                raise RuntimeError(
                    "AsyncSessionMaker not initialized. "
                    "Call 'await init_db()' in your application startup, "
                    "or set DATABASE_URL environment variable."
                )
            return self._maker()
    
    AsyncSessionMaker = LazyAsyncSessionMaker()

async def init_db() -> None:
    """Initialize database connection and create tables if needed."""
    global AsyncSessionMaker, _async_session_maker, _engine
    
    if DATABASE_URL:
        # Using custom DATABASE_URL - create tables for main models
        if _engine:
            async with _engine.begin() as conn:
                await conn.run_sync(BaseModel.metadata.create_all)
    else:
        # Use main DB connection
        if isinstance(AsyncSessionMaker, LazyAsyncSessionMaker):
            await AsyncSessionMaker._ensure_initialized()
            # Replace the lazy wrapper with the actual session maker
            AsyncSessionMaker = AsyncSessionMaker._maker

async def get_session() -> AsyncIterator[AsyncSession]:
    """Get database session."""
    if AsyncSessionMaker is None:
        await init_db()
    async with AsyncSessionMaker() as s:
        yield s

# ---------- API key auth helpers ----------
class ApiKeyAuthError(Exception):
    """Exception raised for API key authentication errors."""
    pass

async def get_api_key_by_token(db: AsyncSession, raw_token: str) -> Optional[ApiKeyModel]:
    """Najde aktivní ApiKey podle plaintext tokenu (prefix + hash compare)."""
    if not raw_token:
        return None
    prefix = raw_token[:API_KEY_PREFIX_LEN]
    q = await db.execute(
        select(ApiKeyModel).where(
            ApiKeyModel.prefix == prefix,
            ApiKeyModel.is_active == True,  # noqa: E712
        )
    )
    candidates: Iterable[ApiKeyModel] = q.scalars().all()
    target_hash = hash_token(raw_token)
    for k in candidates:
        # Use constant-time comparison
        if verify_token(raw_token, k.key_hash):
            # Check expiration
            if k.expires_at and k.expires_at < datetime.now(timezone.utc):
                return None
            return k
    return None

async def require_api_key(
    db: AsyncSession,
    token: Optional[str],
) -> ApiKeyModel:
    """Ověří klíč z hlavičky a vrátí ApiKeyModel; jinak vyhodí ApiKeyAuthError."""
    if not token:
        raise ApiKeyAuthError("Missing API key")
    key = await get_api_key_by_token(db, token)
    if not key:
        raise ApiKeyAuthError("Invalid or inactive API key")
    return key

async def check_rate_limits(db: AsyncSession, *, api_key: ApiKeyModel) -> None:
    """
    Zkontroluje per-minute/hour/day limity a měsíční token/cost kvóty.
    Pokud je překročeno, vyhodí ApiKeyAuthError s popisem.
    """
    now = datetime.now(timezone.utc)

    async def count_since(delta: timedelta) -> int:
        q = await db.execute(
            select(func.count(UsageModel.id)).where(
                UsageModel.api_key_id == api_key.id,
                UsageModel.ts >= (now - delta),
            )
        )
        return int(q.scalar_one() or 0)

    # Per-minute
    if api_key.rate_limit_per_minute:
        used = await count_since(timedelta(minutes=1))
        if used >= int(api_key.rate_limit_per_minute):
            raise ApiKeyAuthError("Rate limit per minute exceeded")

    # Per-hour
    if api_key.rate_limit_per_hour:
        used = await count_since(timedelta(hours=1))
        if used >= int(api_key.rate_limit_per_hour):
            raise ApiKeyAuthError("Rate limit per hour exceeded")

    # Per-day
    if api_key.rate_limit_per_day:
        used = await count_since(timedelta(days=1))
        if used >= int(api_key.rate_limit_per_day):
            raise ApiKeyAuthError("Rate limit per day exceeded")

    # Měsíční tokeny/náklady
    if api_key.max_tokens_per_month or api_key.max_cost_per_month:
        start_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        q = await db.execute(
            select(
                func.coalesce(func.sum(UsageModel.total_tokens), 0),
                func.coalesce(func.sum(UsageModel.cost_usd), 0.0),
            ).where(
                UsageModel.api_key_id == api_key.id,
                UsageModel.ts >= start_month,
                UsageModel.ts < now + timedelta(seconds=1),
            )
        )
        row = q.first()
        total_tokens = int(row[0]) if row and row[0] is not None else 0
        total_cost = float(row[1]) if row and row[1] is not None else 0.0
        if api_key.max_tokens_per_month and total_tokens >= int(api_key.max_tokens_per_month):
            raise ApiKeyAuthError("Monthly token quota exceeded")
        if api_key.max_cost_per_month and total_cost >= float(api_key.max_cost_per_month):
            raise ApiKeyAuthError("Monthly cost quota exceeded")

# ---------- Usage recording ----------
async def record_usage(
    db: AsyncSession,
    *,
    api_key: ApiKeyModel,
    ts: Optional[datetime] = None,
    route: Optional[str] = None,
    deployment: Optional[str] = None,
    model: Optional[str] = None,
    status: Optional[int] = None,
    stream: bool = False,
    prompt_tokens: Optional[int] = None,
    completion_tokens: Optional[int] = None,
    total_tokens: Optional[int] = None,
    stream_bytes: Optional[int] = None,  # Note: Not stored in UsageModel, but kept for API compatibility
    cost_usd: Optional[float] = None,
    meta: Optional[dict] = None,  # Note: Not stored in UsageModel, but can use request_id if needed
) -> UsageModel:
    """
    Record usage in database.
    
    Note: stream_bytes and meta are not stored in UsageModel.
    If meta is provided, it can be stored in request_id field as JSON string.
    """
    # Store meta in request_id if provided (as JSON string)
    request_id = None
    if meta:
        try:
            request_id = json.dumps(meta, ensure_ascii=False)[:128]  # Limit to 128 chars
        except Exception:
            pass  # Ignore JSON serialization errors
    
    u = UsageModel(
        api_key_id=api_key.id,
        ts=ts or datetime.now(timezone.utc),
        route=route,
        deployment=deployment,
        model=model,
        status=status,
        stream=stream,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        cost_usd=cost_usd,
        request_id=request_id,  # Store meta here if provided
    )
    db.add(u)
    api_key.last_used_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(u)
    return u

# ---------- Aggregations (consumption over time) ----------
Bucket = Literal["hour", "day"]

def _date_bucket_expr(bucket: Bucket):
    """Generate date bucket expression for SQL queries."""
    # Get connection string to determine DB type
    conn_str = DATABASE_URL or ComposeConnectionString()
    if conn_str.startswith("sqlite"):
        if bucket == "hour":
            return func.strftime("%Y-%m-%dT%H:00:00Z", UsageModel.ts)
        return func.strftime("%Y-%m-%d", UsageModel.ts)
    # default: Postgres-friendly date_trunc
    return func.to_char(
        func.date_trunc(bucket, UsageModel.ts),
        "YYYY-MM-DD\"T\"HH24:00:00Z" if bucket == "hour" else "YYYY-MM-DD"
    )

async def usage_timeseries_for_key(
    db: AsyncSession,
    *,
    api_key_id: uuid.UUID,  # Changed from str to UUID
    since: datetime,
    until: datetime,
    bucket: Bucket = "day",
):
    """Get usage timeseries data for an API key."""
    b = _date_bucket_expr(bucket).label("bucket")
    q = (
        select(
            b,
            func.count().label("requests"),
            func.sum(UsageModel.prompt_tokens).label("prompt_tokens"),
            func.sum(UsageModel.completion_tokens).label("completion_tokens"),
            func.sum(UsageModel.total_tokens).label("total_tokens"),
            func.sum(UsageModel.cost_usd).label("cost_usd"),
        )
        .where(
            UsageModel.api_key_id == api_key_id,
            UsageModel.ts >= since,
            UsageModel.ts < until
        )
        .group_by(b)
        .order_by(b.asc())
    )
    res = await db.execute(q)
    rows = res.mappings().all()
    return [dict(r) for r in rows]

# Export for backward compatibility
# Note: ApiKey, User, Usage are now aliases to main models
ApiKey = ApiKeyModel
User = UserModel
Usage = UsageModel
