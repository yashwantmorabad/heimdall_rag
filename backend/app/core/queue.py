"Reddis connection pool for arq jobs."

from contextlib import asynccontextmanager
from arq import create_pool
from app.core.config import get_settings
from arq.connections import RedisSettings

_redis_pool = None
async def get_redis_pool():
    "Get or create the global Redis connection pool."
    global _redis_pool
    if _redis_pool is None:
        settings = get_settings()
        # Parse redis_url and use 127.0.0.1 instead of localhost for Windows async compatibility
        from urllib.parse import urlparse
        parsed = urlparse(settings.redis_url)
        host = parsed.hostname or "localhost"
        if host == "localhost":
            host = "127.0.0.1"
        _redis_pool = await create_pool(
            RedisSettings(
                host=host,
                port=parsed.port or 6379,
                database=int(parsed.path.lstrip("/")) if parsed.path else 0,
                password=parsed.password or None,
            ),
            default_queue_name="heimdall:jobs",
        )
    return _redis_pool

async def close_redis_pool():
    "Close the redis connection pool on shutdown."
    global _redis_pool
    if _redis_pool:
        await _redis_pool.close()
        _redis_pool = None

@asynccontextmanager
async def redis_lifespan(app):
    "FastAPI lifespan handler for redis pool."
    await get_redis_pool()
    yield
    await close_redis_pool()

_all__ = ["get_redis_pool", "close_redis_pool", "redis_lifespan"]