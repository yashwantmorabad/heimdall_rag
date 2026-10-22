"""Integration test for CLI ingestion (real DB)."""

import asyncio
import tempfile
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.session import AsyncSessionLocal
from app.db.models.chunk import Chunk as ChunkModel
from app.db.models.document import Document
from app.db.models.tenant import Tenant
from app.rag.ingestion.pipeline import ingest_file


# Default dev tenant (matches CLI)
TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
async def db_session():
    """Provide a clean DB session for each test."""
    async with AsyncSessionLocal() as session:
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
        # Ensure document exists
        await db_session.execute(
            pg_insert(Document).values(
                id=document_id,
                tenant_id=TENANT_ID,
                filename="test.txt",
                status="ready",
            ).on_conflict_do_nothing(index_elements=["id"])
        )
        await db_session.commit()

        # Run ingestion
        stored = await ingest_file(txt_path, TENANT_ID, document_id)

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
async def test_ingest_idempotent(db_session):
    """Re-ingesting same document does not create duplicates."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Idempotency test. Running twice should not duplicate chunks.")
        txt_path = Path(f.name)

    document_id = UUID("33333333-3333-3333-3333-333333333333")

    try:
        # Ensure tenant exists
        await db_session.execute(
            pg_insert(Tenant).values(id=TENANT_ID, name="dev-tenant").on_conflict_do_nothing(index_elements=["id"])
        )
        # Ensure document exists
        await db_session.execute(
            pg_insert(Document).values(
                id=document_id,
                tenant_id=TENANT_ID,
                filename="test.txt",
                status="ready",
            ).on_conflict_do_nothing(index_elements=["id"])
        )
        await db_session.commit()

        # First ingestion
        stored1 = await ingest_file(txt_path, TENANT_ID, document_id)
        assert stored1 > 0

        # Second ingestion (same document_id)
        stored2 = await ingest_file(txt_path, TENANT_ID, document_id)

        # Should insert 0 new chunks (ON CONFLICT DO NOTHING)
        assert stored2 == 0

        # Verify total chunks unchanged
        result = await db_session.execute(
            select(ChunkModel).where(ChunkModel.document_id == document_id)
        )
        chunks = result.scalars().all()
        assert len(chunks) == stored1

    finally:
        txt_path.unlink(missing_ok=True)