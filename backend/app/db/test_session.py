"""Test database session factory (uses TEST_DATABASE_URL)."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()
if not settings.test_database_url:
    raise RuntimeError("TEST_DATABASE_URL not set in .env")

test_engine = create_async_engine(settings.test_database_url, pool_pre_ping=True)
AsyncTestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


async def get_test_session() -> AsyncSession:
    async with AsyncTestSessionLocal() as session:
        yield session