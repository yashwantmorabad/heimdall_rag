"""Integration test for CLI ingestion (real DB)."""

import asyncio
import tempfile
from pathlib import Path
from uuid import UUID

import pytest
import pytest_asyncio
from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.test_session import AsyncTestSessionLocal
from app.db.models.chunk import Chunk as ChunkModel
from app.db.models.document import Document
from app.db.models.tenant import Tenant
from app.rag.ingestion.pipeline import ingest_file
from sqlalchemy.ext.asyncio import async_sessionmaker


# Default dev tenant (matches CLI)
TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")


@pytest_asyncio.fixture
async def db_session():
    """Provide a clean test DB session for each test."""
    async with AsyncTestSessionLocal() as session:
        yield session


@pytest.mark.asyncio
async def test_ingest_txt_file(db_session):
    """Full pipeline: ingest a TXT file end-to-end."""
    # Create a temporary text file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Hello world. This is a test document. It has multiple sentences. ")
        f.write("We want to see it chunked, embedded, and stored.")
        txt_path = Path(f.name)

    document_id = UUID("22222222-2222-2222-2222-222222222222")

    try:
        # Ensure tenant exists
        await db_session.execute(
            pg_insert(Tenant).values(id=TENANT_ID, name="dev-tenant").on_conflict_do_nothing(index_elements=["id"])
        )
        # Ensure document exists - use unique filename to avoid unique constraint conflict
        await db_session.execute(
            pg_insert(Document).values(
                id=document_id,
                tenant_id=TENANT_ID,
                filename="test_ingest_txt_file.txt",
                status="ready",
            ).on_conflict_do_nothing(index_elements=["id"])
        )
        await db_session.commit()

        # Run ingestion
        stored = await ingest_file(txt_path, TENANT_ID, document_id, session_factory=AsyncTestSessionLocal)

        # Verify chunks stored
        assert stored > 0

        # Query DB to verify
        result = await db_session.execute(
            select(ChunkModel).where(ChunkModel.document_id == document_id)
        )
        chunks = result.scalars().all()
        assert len(chunks) == stored
        assert all(c.tenant_id == TENANT_ID for c in chunks)
        assert all(c.embedding is not None for c in chunks)
        assert all(len(c.embedding) == 384 for c in chunks)
        assert all(c.embedding_model == "BAAI/bge-small-en-v1.5" for c in chunks)

    finally:
        txt_path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_ingest_without_precreating_document(db_session):
    """
    Regression test: ingest_file called without pre-creating Document row.
    This is the exact code path the CLI uses.
    Before fix: fails with ForeignKeyViolationError on chunks_document_id_fkey.
    After fix: should create document + chunks successfully.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Regression test. This file has no pre-created document row.")
        txt_path = Path(f.name)

    # No document_id passed - ingest_file will generate one
    # No pre-created Document row - this is the CLI path

    try:
        # Ensure tenant exists (same as other tests)
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from app.db.models.tenant import Tenant
        await db_session.execute(
            pg_insert(Tenant).values(id=TENANT_ID, name="dev-tenant").on_conflict_do_nothing(index_elements=["id"])
        )
        await db_session.commit()

        # This is the CLI code path: no document_id, no pre-created document
        stored = await ingest_file(txt_path, TENANT_ID, session_factory=AsyncTestSessionLocal)

        # After fix: should succeed and return chunk count > 0
        assert stored > 0

        # Verify document was created
        from app.db.models.document import Document
        from sqlalchemy import select
        result = await db_session.execute(
            select(Document).where(Document.tenant_id == TENANT_ID, Document.filename == txt_path.name)
        )
        doc = result.scalar_one_or_none()
        assert doc is not None
        assert doc.status == "ready"

        # Verify chunks exist
        from app.db.models.chunk import Chunk as ChunkModel
        result = await db_session.execute(
            select(ChunkModel).where(ChunkModel.document_id == doc.id)
        )
        chunks = result.scalars().all()
        assert len(chunks) == stored

    except Exception as e:
        # Before fix: ForeignKeyViolationError
        # Re-raise to show the test fails as expected
        raise
    finally:
        txt_path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_ingest_replaces_chunks_on_reingest(db_session):
    """Re-ingesting same document REPLACES chunks (new behavior: DELETE + INSERT)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Re-ingest test. Running twice should REPLACE chunks.")
        txt_path = Path(f.name)

    document_id = UUID("33333333-3333-3333-3333-333333333333")

    try:
        # Ensure tenant exists
        await db_session.execute(
            pg_insert(Tenant).values(id=TENANT_ID, name="dev-tenant").on_conflict_do_nothing(index_elements=["id"])
        )
        # Ensure document exists - use unique filename to avoid unique constraint conflict
        await db_session.execute(
            pg_insert(Document).values(
                id=document_id,
                tenant_id=TENANT_ID,
                filename="test_ingest_replaces.txt",
                status="ready",
            ).on_conflict_do_nothing(index_elements=["id"])
        )
        await db_session.commit()

        # First ingestion
        stored1 = await ingest_file(txt_path, TENANT_ID, document_id, session_factory=AsyncTestSessionLocal)
        assert stored1 > 0

        # Second ingestion (same document_id) - should REPLACE chunks, not skip
        stored2 = await ingest_file(txt_path, TENANT_ID, document_id, session_factory=AsyncTestSessionLocal)

        # New behavior: replaces chunks, so same count returned
        assert stored2 == stored1

        # Verify total chunks unchanged (replaced, not duplicated)
        result = await db_session.execute(
            select(ChunkModel).where(ChunkModel.document_id == document_id)
        )
        chunks = result.scalars().all()
        assert len(chunks) == stored1

    finally:
        txt_path.unlink(missing_ok=True)