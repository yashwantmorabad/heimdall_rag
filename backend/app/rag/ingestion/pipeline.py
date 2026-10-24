"""Ingestion pipeline: parse->clean->chunk->embed->store"""

from app.rag.ingestion.embedder import ChunkDataclass
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import delete, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.rag.ingestion.parsers import parse_file, ParsedPage
from app.rag.ingestion.cleaner import clean_text
from app.rag.ingestion.chunker import chunk_file
from app.rag.ingestion.embedder import embed_chunks
from app.db.session import AsyncSessionLocal
from app.db.models.document import Document
from app.db.models.chunk import Chunk as ChunkModel


async def ingest_file(
    file_path: Path,
    tenant_id: UUID,
    document_id: UUID | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> int:
    """
    Run the full ingestion pipeline for a single file.

    Args:
        file_path: path to the document,
        tenant_id: Tenant UUID (for isolation).
        document_id: Optional document UUID (generated if not provided).

    Returns:
        Number of chunks stored (0 if already ingested or empty)
    """

    if session_factory is None:
        session_factory = AsyncSessionLocal

    # 1. Parse
    pages: list[ParsedPage] = parse_file(file_path)

    # 2. Clean (per page)
    cleaned_pages = [
        ParsedPage(page_number=p.page_number, text=clean_text(p.text))
        for p in pages
    ]

    # 3. Chunk
    file_type = file_path.suffix.lower().lstrip(".")
    chunks: list[ChunkDataclass] = chunk_file(
        cleaned_pages,
        token_counter=lambda t: len(t.split()),
        chunk_size=500,
        chunk_overlap=75,
        file_type=file_type,
    )

    # 4. Embed (loads model, computes embeddings)
    chunks = embed_chunks(chunks)

    if not chunks:
        return 0

    # TXN 1: Get or create document with status="processing"
    async with session_factory() as session:
        if document_id is None:
            # Check for existing document by (tenant_id, filename)
            result = await session.execute(
                select(Document.id).where(
                    Document.tenant_id == tenant_id,
                    Document.filename == file_path.name,
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                document_id = existing
                # Reset status to processing for re-ingestion
                await session.execute(
                    update(Document)
                    .where(Document.id == document_id)
                    .values(status="processing", error=None)
                )
            else:
                document_id = uuid4()
                session.add(
                    Document(
                        id=document_id,
                        tenant_id=tenant_id,
                        filename=file_path.name,
                        status="processing",
                    )
                )
        else:
            # Update existing document to "processing"
            await session.execute(
                update(Document)
                .where(Document.id == document_id)
                .values(status="processing", error=None)
            )
        await session.commit()

    # TXN 2: Delete old chunks + insert new ones
    inserted = 0
    try:
        async with session_factory() as session:
            # Delete old chunks for this document
            await session.execute(
                delete(ChunkModel).where(ChunkModel.document_id == document_id)
            )

            # Insert new chunks
            for i, chunk in enumerate(chunks):
                stmt = (
                    pg_insert(ChunkModel)
                    .values(
                        tenant_id=tenant_id,
                        document_id=document_id,
                        content=chunk.text,
                        chunk_index=i,
                        page=chunk.page_number,
                        embedding=chunk.embedding,
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
    except Exception:
        # If chunk insertion fails, mark document as failed
        async with session_factory() as session:
            await session.execute(
                update(Document)
                .where(Document.id == document_id)
                .values(status="failed", error="Chunk insertion failed")
            )
            await session.commit()
        raise

    # TXN 3: Mark document as ready (or failed if no chunks)
    async with session_factory() as session:
        status = "ready" if inserted > 0 else "failed"
        error = None if inserted > 0 else "No chunks extracted"
        await session.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(status=status, error=error)
        )
        await session.commit()

    return inserted


# Line-by-line explanation
# Lines: What it does
# TXN 1: Gets or creates Document row with status="processing", commits immediately
# TXN 2: Deletes old chunks, inserts new chunks in single transaction, commits
# TXN 3: Updates Document status to "ready" or "failed", commits
# If TXN 2 fails: old chunks preserved (DELETE+INSERT atomic), doc marked "failed"
# Unique constraint on (tenant_id, filename) prevents duplicates (new migration)