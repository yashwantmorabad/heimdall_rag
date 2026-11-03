"""Tenant isolation tests for vector retrieval."""

import pytest
import pytest_asyncio
from uuid import UUID, uuid4

from app.rag.retrieval.vector_search import search_chunks
from app.rag.ingestion.embedder import fake_embed_chunks
from app.rag.ingestion.chunker import Chunk as ChunkDataclass
from app.db.session import AsyncSessionLocal
from tests.conftest import AsyncTestSessionLocal
from app.db.models.chunk import Chunk as ChunkModel
from app.db.models.document import Document
from app.db.models.tenant import Tenant


TENANT_A = UUID("11111111-1111-1111-1111-111111111111")
TENANT_B = UUID("22222222-2222-2222-2222-222222222222")


@pytest_asyncio.fixture
async def isolation_data():
    """Create two tenants with identical content but different embeddings."""
    async with AsyncTestSessionLocal() as session:
        # Create tenants
        session.add_all([
            Tenant(id=TENANT_A, name="Tenant A"),
            Tenant(id=TENANT_B, name="Tenant B"),
        ])
        await session.commit()

        # Create documents
        doc_a = Document(id=uuid4(), tenant_id=TENANT_A, filename="tenant_a.pdf", status="ready")
        doc_b = Document(id=uuid4(), tenant_id=TENANT_B, filename="tenant_b.pdf", status="ready")
        session.add_all([doc_a, doc_b])
        await session.commit()

        # Identical text for both tenants - tests that tenant filter works, not content
        text = "The library late fee is $1 per day after the due date."
        
        chunks_a = fake_embed_chunks([
            ChunkDataclass(text=text, token_count=20, page_number=1, chunk_index=0)
        ])
        chunks_b = fake_embed_chunks([
            ChunkDataclass(text=text, token_count=20, page_number=1, chunk_index=0)
        ])

        for chunk in chunks_a:
            session.add(ChunkModel(
                tenant_id=TENANT_A, document_id=doc_a.id,
                content=chunk.text, chunk_index=chunk.chunk_index,
                page=chunk.page_number, embedding=chunk.embedding,
                embedding_model=chunk.embedding_model,
            ))
        for chunk in chunks_b:
            session.add(ChunkModel(
                tenant_id=TENANT_B, document_id=doc_b.id,
                content=chunk.text, chunk_index=chunk.chunk_index,
                page=chunk.page_number, embedding=chunk.embedding,
                embedding_model=chunk.embedding_model,
            ))
        await session.commit()

    # Return doc IDs for assertions
    yield {"doc_a_id": doc_a.id, "doc_b_id": doc_b.id}

    # Cleanup
    async with AsyncTestSessionLocal() as session:
        await session.execute(ChunkModel.__table__.delete())
        await session.execute(Document.__table__.delete())
        await session.execute(Tenant.__table__.delete())
        await session.commit()


async def test_tenant_a_search_never_returns_tenant_b_chunks(isolation_data):
    """Tenant A searching for 'late fee' must only get Tenant A's chunk."""
    results = await search_chunks(
        TENANT_A, "What is the library late fee?", top_k=10,
        session_factory=AsyncTestSessionLocal
    )

    # Should find exactly 1 chunk (Tenant A's)
    assert len(results) == 1
    assert results[0].document_id == isolation_data["doc_a_id"]


async def test_tenant_b_search_never_returns_tenant_a_chunks(isolation_data):
    """Tenant B searching for 'late fee' must only get Tenant B's chunk."""
    results = await search_chunks(
        TENANT_B, "What is the library late fee?", top_k=10,
        session_factory=AsyncTestSessionLocal
    )

    assert len(results) == 1
    assert results[0].document_id == isolation_data["doc_b_id"]