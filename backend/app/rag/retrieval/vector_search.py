"""Vector retrieval with tenant-scoped cosine search."""

import asyncio
from uuid import UUID
from typing import List
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.ingestion.embedder import embed_queries
from app.db.models.chunk import Chunk as ChunkModel
from app.db.models.document import Document


@dataclass(frozen=True)
class RetrievedChunk:
    """A chunk returned from vector search with metadata for citations."""
    document_id: UUID
    filename: str
    page: int | None
    chunk_index: int
    context: str
    distance: float  # 0 = same direction, 1 = opposite direction


async def vector_search(
    session: AsyncSession,
    tenant_id: UUID,
    question: str,
    top_k: int = 20,
) -> List[RetrievedChunk]:
    """
    Embed the question and run cosine similarity search scoped to tenant.

    Args:
        session: async database session.
        tenant_id: tenant ID.
        question: question to search for.
        top_k: number of results to return.

    Returns:
        List[RetrievedChunk]: list of retrieved chunks
    """
    # 1. Embed the question with 'search_query: ' prefix (non-blocking)
    question_embeddings = await asyncio.to_thread(embed_queries, [question])
    question_embedding = question_embeddings[0]

    # 2. Cosine search with tenant filter inside the SQL
    # JOIN documents to get filename; ORDER BY distance ASC (nearest first)
    stmt = (
        select(
            ChunkModel.document_id,
            Document.filename,
            ChunkModel.page,
            ChunkModel.chunk_index,
            ChunkModel.content,
            ChunkModel.embedding.cosine_distance(question_embedding).label("distance"),
        )
        .join(Document, ChunkModel.document_id == Document.id)
        .where(ChunkModel.tenant_id == tenant_id)
        .order_by(text("distance"))
        .limit(top_k)
    )
    result = await session.execute(stmt)
    rows = result.all()

    return [
        RetrievedChunk(
            document_id=row.document_id,
            filename=row.filename,
            page=row.page,
            chunk_index=row.chunk_index,
            context=row.content,
            distance=row.distance,
        )
        for row in rows
    ]


# Convenience: open session, run vector_search, close session
from app.db.session import AsyncSessionLocal


async def search_chunks(
    tenant_id: UUID,
    question: str,
    top_k: int = 20,
    session_factory=AsyncSessionLocal,
) -> List[RetrievedChunk]:
    """
    Convenience: open session, run vector_search, close session.
    Used by CLI and tests. Accepts optional session_factory for test injection.
    """
    async with session_factory() as session:
        return await vector_search(session, tenant_id, question, top_k)