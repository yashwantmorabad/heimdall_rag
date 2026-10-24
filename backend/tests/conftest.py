"""Pytest fixtures for integration tests (test database only)."""

import sys
from pathlib import Path

# Ensure backend directory is on sys.path for imports like "app.core.config"
BACKEND_DIR = Path(__file__).parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest
import pytest_asyncio
from sqlalchemy import text, delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.db.models.chunk import Chunk as ChunkModel
from app.db.models.document import Document
from app.db.models.tenant import Tenant


# ──────────────────────────────────────────────────────────────────────────────
# Test engine with NullPool (no connection pooling → no event-loop affinity)
# ──────────────────────────────────────────────────────────────────────────────
def _make_test_engine():
    settings = get_settings()
    if not settings.test_database_url:
        raise RuntimeError("TEST_DATABASE_URL not set in .env")
    return create_async_engine(
        settings.test_database_url,
        pool_pre_ping=True,
        poolclass=NullPool,   # <-- key fix: no pooled connections across loops
    )


_test_engine = _make_test_engine()
AsyncTestSessionLocal = async_sessionmaker(_test_engine, expire_on_commit=False)


# ──────────────────────────────────────────────────────────────────────────────
# Guard: abort the whole run if we're not on a *_test database
# ──────────────────────────────────────────────────────────────────────────────
@pytest_asyncio.fixture(scope="session", autouse=True)
async def guard_test_database():
    """Run once at session start. Exit if active DB isn't a test database."""
    engine = _make_test_engine()
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT current_database()"))
        db_name = result.scalar()
    await engine.dispose()

    if not db_name.endswith("_test"):
        pytest.exit(f"❌ Refusing to run tests on non-test database: {db_name}")


# ──────────────────────────────────────────────────────────────────────────────
# Per-test session fixture with automatic cleanup
# ──────────────────────────────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    """Provide a clean test DB session. Truncates test tables after each test."""
    async with AsyncTestSessionLocal() as session:
        yield session

    # Cleanup: truncate test tables in correct FK order (children first)
    async with AsyncTestSessionLocal() as session:
        await session.execute(delete(ChunkModel))
        await session.execute(delete(Document))
        await session.execute(delete(Tenant))
        await session.commit()


# ──────────────────────────────────────────────────────────────────────────────
# Backward-compat export (if any test imports AsyncTestSessionLocal directly)
# ──────────────────────────────────────────────────────────────────────────────
__all__ = ["AsyncTestSessionLocal", "db_session", "guard_test_database"]