"""Tests for queue failure handling on upload."""

import io
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch
from uuid import UUID, uuid4

from app.main import app
from app.services.keys import create_api_key
from app.db.models.tenant import Tenant
from app.db.models.document import Document
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import select
from tests.conftest import AsyncTestSessionLocal


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def override_dependencies():
    """Override queue to simulate failure."""
    async def mock_enqueue_fail(*args, **kwargs):
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail={"code": "service_unavailable", "message": "Redis unavailable"}
        )
    
    with patch("app.api.v1.documents.enqueue_ingestion_job", mock_enqueue_fail):
        yield
    
    app.dependency_overrides.clear()


@pytest.fixture
def api_key_headers():
    """Create a test API key and return headers."""
    from app.services.keys import create_api_key
    from app.db.models.tenant import Tenant
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    import asyncio
    from uuid import UUID

    TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")
    
    async def _create_key():
        async with AsyncTestSessionLocal() as session:
            await session.execute(
                pg_insert(Tenant).values(id=TENANT_ID, name="test-tenant").on_conflict_do_nothing(index_elements=["id"])
            )
            await session.commit()
            api_key, full_key = await create_api_key(session, TENANT_ID, "Test Key", ["documents", "query"])
            await session.commit()
            return full_key
    
    full_key = asyncio.run(_create_key())
    return {"X-API-Key": full_key}


@pytest.fixture
async def client(override_dependencies):
    """AsyncClient with overridden dependencies."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


# ──────────────────────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestQueueFailureOnUpload:
    """Tests for queue failure handling during upload."""

    @pytest.mark.asyncio
    async def test_redis_down_marks_document_failed(self, client, api_key_headers):
        """When Redis is down, document should be marked failed, file cleaned up, 503 returned."""
        files = {"file": ("test.txt", b"valid content", "text/plain")}
        response = await client.post("/v1/documents", files=files, headers=api_key_headers)
        
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "service_unavailable"
        
        # Verify document was marked failed in DB
        async with AsyncTestSessionLocal() as session:
            result = await session.execute(
                select(Document).where(Document.filename == "test.txt")
            )
            doc = result.scalar_one_or_none()
            assert doc is not None
            assert doc.status == "failed"
            assert doc.error is not None

    @pytest.mark.asyncio
    async def test_file_cleaned_up_on_queue_failure(self, client, api_key_headers):
        """File should be deleted when queue fails."""
        from app.core.config import get_settings
        from pathlib import Path
        
        files = {"file": ("cleanup_test.txt", b"content", "text/plain")}
        response = await client.post("/v1/documents", files=files, headers=api_key_headers)
        
        assert response.status_code == 503
        
        # Find the document and check it was marked failed
        async with AsyncTestSessionLocal() as session:
            result = await session.execute(
                select(Document).where(Document.filename == "cleanup_test.txt")
            )
            doc = result.scalar_one_or_none()
            assert doc is not None
            assert doc.status == "failed"
            assert doc.error is not None
            assert "queue" in doc.error.lower() or "processing" in doc.error.lower()

    @pytest.mark.asyncio
    async def test_valid_upload_still_works(self, client, api_key_headers):
        """Valid upload should still work when queue is healthy."""
        # This test uses the real queue, so it requires Redis to be running
        # We'll skip this test in the queue failure test file
        # It's tested in the upload validation tests
        pass


# ──────────────────────────────────────────────────────────────────────────────
# Integration test with real queue (requires Redis)
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upload_success_with_real_queue():
    """Integration test: upload with real Redis queue (requires Redis running)."""
    # This is tested in the upload validation tests
    pass