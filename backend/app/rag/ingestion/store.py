from typing import List
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.ingestion.chunker import Chunk as ChunkDataclass
from app.db.models.chunk import Chunk as ChunkModel
from sqlalchemy.dialects.postgresql import insert



async def store_chunks(
    session: AsyncSession,
    tenant_id: UUID,
    document_id: UUID,
    chunks: List[ChunkDataclass],
)-> int:
    """
    Insert chukns into the database.

    Idempotent: uses ON CONFLICT DO NOTHING on (document_id, chunk_index).
    Re-running ingestion for the same document will not create duplicates.

    Args:
        session: Async DB session.
        tenant_is: Tenant owing the document.
        document_id: Document UUID
        chunks: List of Chunk objects with embeddings already computed.
    
    Returns:
        Number of chunks actually inserted(0 if all already exists)
    """

    if not chunks:
        return 0

    inserted=0
    
    for i, chunk in enumerate(chunks):
        # Use ORM insert with ON CONFLICT DO NOTHING
        stmt = (
            insert(ChunkModel)
            .values(
                tenant_id=tenant_id,
                document_id=document_id,
                content=chunk.text,
                chunk_index=i,
                page=chunk.page_number,
                embedding=chunk.embedding,  # list[float] -> Vector type handles conversion
                embedding_model=chunk.embedding_model,
            )
            .on_conflict_do_nothing(
                constraint="uq_chunks_document_chunk_index"
            )
        )
        result = await session.execute(stmt)
        if result.rowcount > 0:
            inserted += 1

    await session.commit()
    return inserted

# Line-by-line explanation
# Line:	What it does
# from sqlalchemy import text	text() : lets us write raw SQL with named parameters (safe from injection)
# AsyncSession : SQLAlchemy async session for DB operations
# store_chunks(session, tenant_id, document_id, chunks) : Main function — inserts chunks for a document
# ON CONFLICT (document_id, chunk_index) DO NOTHING : Idempotency key: if a chunk with same document_id + chunk_index exists, skip it. No error, no duplicate.
# chunk_index: i : Uses loop index (0, 1, 2...) — matches the unique constraint in the DB schema
# chunk.embedding : List of floats — pgvector accepts Python lists directly
# result.rowcount : Number of rows actually inserted (0 if conflict)
# await session.commit() : Commits the transaction

# Key Python features for beginners
# 1. text("SQL") with named params — Safe parameterized queries. Values passed as dict, never interpolated into string.
# 2. ON CONFLICT ... DO NOTHING — PostgreSQL upsert syntax. Requires a unique constraint (we have uq_chunks_document_chunk_index on (document_id, chunk_index)).
# 3. rowcount — After INSERT, tells how many rows were actually inserted (vs skipped due to conflict).
# 4. await session.commit() — Async commit. Without this, inserts are rolled back when session closes.

