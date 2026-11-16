"""Pytest fixtures for integration tests (test database only)."""

import sys
from pathlib import Path
from urllib.parse import urlparse

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
# Guard: validate TEST_DATABASE_URL BEFORE any engine is created
# ──────────────────────────────────────────────────────────────────────────────
def validate_test_database_url(url: str|None)-> None:
    """
    Ensure the test database URL points to a database whose name ends with '_test'.
    Raises RuntimeError with a clear message if not.
    """
    if not url:
        raise RuntimeError("TEST_DATABASE_URL not set.")
    # Extract database name from postgresql://user:pass@host:port/dbname
    parsed = urlparse(url)
    db_name = parsed.path.lstrip("/")
    if not db_name:
        raise RuntimeError("TEST_DATABASE_URL has no database name.")
    if not db_name.endswith("_test"):
        raise RuntimeError(f"Refusing to run tests on non-test database: {db_name}.")

settings = get_settings()
validate_test_database_url(settings.test_database_url)

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
__all__ = ["AsyncTestSessionLocal", "db_session"]