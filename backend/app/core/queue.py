"Reddis connection pool for arq jobs."

from contextlib import asynccontextmanager
from arq import create_pool
from arq.core.config import get_settings
from arq.core.connections import RedisSettings

_redis_pool = None
async def get_redis_pool():
    "Get or create the global Redis connection pool."
    global _redis_pool
    if _redis_pool is None:
        settings = get_settings()
        # Parse redis_url
        from urllib.parse import urlparse
        parsed = urlparse(settings.redis_url)
        _redis_pool = await create_pool(
            RedisSettings(
                host=parsed.hostname or "localhost",
                port=parsed.port or 6379,
                database=int(parsed.path.lstrip("/")) if parsed.path else 0,
                password=parsed.password or None,
            )
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