"""Tests for DELETE /v1/documents/{id} endpoint."""

import io
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch
from uuid import UUID, uuid4

from app.main import app
from app.services.keys import create_api_key
from app.services.documents import delete_document

from app.db.models.document import Document
from app.db.models.tenant import Tenant
from app.db.models.chunk import Chunk as ChunkModel
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import select

from tests.conftest import AsyncTestSessionLocal, override_get_session


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def override_dependencies():
    """Override queue to mock enqueue."""
    async def mock_enqueue(*args, **kwargs):
        return None
    
    with patch("app.api.v1.documents.enqueue_ingestion_job", mock_enqueue):
        yield
    
    app.dependency_overrides.clear()


@pytest.fixture
def api_key_headers(db_session):
    """Create a test API key and return headers using the test session."""
    from app.services.keys import create_api_key
    from app.db.models.tenant import Tenant
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from uuid import UUID

    TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")
    
    async def _create_key():
        # Use the test session (db_session) which is already set up with the test database
        await db_session.execute(
            pg_insert(Tenant).values(id=TENANT_ID, name="test-tenant").on_conflict_do_nothing(index_elements=["id"])
        )
        await db_session.commit()
        api_key, full_key = await create_api_key(db_session, TENANT_ID, "Test Key", ["documents", "query"])
        await db_session.commit()
        return full_key
    
    # We need to run this async function - use the event loop from the test
    import asyncio
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

class TestDeleteDocument:
    """Tests for DELETE /v1/documents/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_document_cascades_chunks(self, client, api_key_headers, db_session):
        """DELETE should remove document, its chunks, and the stored file."""
        # Upload a document via the API to ensure proper tenant association
        files = {"file": ("test_delete.txt", b"Test chunk 0\nTest chunk 1\nTest chunk 2", "text/plain")}
        upload_resp = await client.post("/v1/documents", files=files, headers=api_key_headers)
        assert upload_resp.status_code == 202
        doc_id = upload_resp.json()["document_id"]
        
        # Manually set document to ready and add chunks (bypass worker)
        async with AsyncTestSessionLocal() as session:
            from app.db.models.document import Document
            from app.db.models.chunk import Chunk as ChunkModel
            import numpy as np
            
            doc = await session.get(Document, UUID(doc_id))
            assert doc is not None
            doc.status = "ready"
            
            # Add chunks
            for i in range(3):
                session.add(ChunkModel(
                    id=uuid4(),
                    tenant_id=doc.tenant_id,
                    document_id=doc.id,
                    content=f"Test chunk {i}",
                    chunk_index=i,
                    page=1,
                    embedding=np.random.rand(768).astype(np.float32).tolist(),
                    embedding_model="nomic-embed-text",
                ))
            await session.commit()
        
        # Verify document and chunks exist before delete
        async with AsyncTestSessionLocal() as session:
            from app.db.models.document import Document
            from app.db.models.chunk import Chunk as ChunkModel
            from sqlalchemy import select
            
            doc = await session.get(Document, UUID(doc_id))
            assert doc is not None
            assert doc.status == "ready"
            
            result = await session.execute(
                select(ChunkModel).where(ChunkModel.document_id == UUID(doc_id))
            )
            chunks = result.scalars().all()
            assert len(chunks) >= 1
        
        
        
        # Now delete
        delete_resp = await client.delete(f"/v1/documents/{doc_id}", headers=api_key_headers)
        assert delete_resp.status_code == 204
        
        # Verify document is gone
        async with AsyncTestSessionLocal() as session:
            doc = await session.get(Document, doc_id)
            assert doc is None
            
            # Verify chunks are also gone (cascading delete)
            result = await session.execute(
                select(ChunkModel).where(ChunkModel.document_id == doc_id)
            )
            chunks = result.scalars().all()
            assert len(chunks) == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent_document_returns_404(self, client, api_key_headers):
        """Deleting non-existent document returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.delete(f"/v1/documents/{fake_id}", headers=api_key_headers)
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "not_found"

    @pytest.mark.asyncio
    async def test_delete_removes_stored_file(self, client, api_key_headers):
        """DELETE should also remove the stored file from disk."""
        from app.core.config import get_settings
        from pathlib import Path
        
        files = {"file": ("file_to_delete.txt", b"delete me", "text/plain")}
        upload_resp = await client.post("/v1/documents", files=files, headers=api_key_headers)
        assert upload_resp.status_code == 202
        doc_id = upload_resp.json()["document_id"]
        
        # Find the stored file path
        settings = get_settings()
        storage_root = Path(settings.storage_path).resolve()
        TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")
        tenant_dir = storage_root / str(TENANT_ID)
        
        # Find the file
        file_path = None
        for ext in (".pdf", ".txt", ".md"):
            candidate = tenant_dir / f"{doc_id}{ext}"
            if candidate.exists():
                file_path = candidate
                break
        
        assert file_path is not None
        assert file_path.exists()
        
        # Delete the document
        delete_resp = await client.delete(f"/v1/documents/{doc_id}", headers=api_key_headers)
        assert delete_resp.status_code == 204
        
        # Verify file is deleted
        assert not file_path.exists()

    @pytest.mark.asyncio
    async def test_delete_cross_tenant_isolation(self, client, api_key_headers):
        """Tenant B cannot delete Tenant A's document (returns 404)."""
        from app.services.keys import create_api_key
        from app.db.models.tenant import Tenant
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from uuid import UUID
        import asyncio
        
        # Create tenant B
        TENANT_B = UUID("22222222-2222-2222-2222-222222222222")
        async with AsyncTestSessionLocal() as session:
            from sqlalchemy.dialects.postgresql import insert as pg_insert
            from app.db.models.tenant import Tenant
            await session.execute(
                pg_insert(Tenant).values(id=TENANT_B, name="tenant-b").on_conflict_do_nothing(index_elements=["id"])
            )
            await session.commit()
            key_b, full_key_b = await create_api_key(session, UUID("22222222-2222-2222-2222-222222222222"), "Key B", ["documents", "query"])
            await session.commit()
        
        # Tenant A uploads a document
        files = {"file": ("tenant_a_doc.txt", b"tenant a content", "text/plain")}
        upload_resp = await client.post("/v1/documents", files=files, headers=api_key_headers)
        assert upload_resp.status_code == 202
        doc_id = upload_resp.json()["document_id"]
        
        # Tenant B tries to delete it - should get 404
        headers_b = {"X-API-Key": full_key_b}
        response = await client.delete(f"/v1/documents/{doc_id}", headers=headers_b)
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "not_found"
        
        # Tenant A can still delete it
        delete_resp = await client.delete(f"/v1/documents/{doc_id}", headers=api_key_headers)
        assert delete_resp.status_code == 204