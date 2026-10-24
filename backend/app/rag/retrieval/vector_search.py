"Vector retrieval with tenant-scoped cosine search."
from sqlalchemy.util import await_fallback
from sqlalchemy.engine import result
from transformers.models import falcon
from pyexpat import model
from ast import List
from uuid import UUID
from typing  import list 
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.ingestion.embedder import embed_texts,get_embedding_model
from app.db.models.chunk import Chunk as ChunkModel
from app.db.models.document import Document
from app.core.config import get_settings

# Line-by-line:
# - UUID — tenant_id and document_id are UUIDs.
# - dataclass — for the return type (clean, typed, no boilerplate).
# - select, text — SQLAlchemy query builder + raw SQL for the <=> operator.
# - AsyncSession — async database session.
# - embed_texts, get_embedding_model — reuse the ingestion embedder (same model, same normalization).
# - ChunkModel, Document — ORM models for the JOIN.

# Chunk2: Result dataclass and search function.

@dataclass(frozen=True)
class RetrievedChunk:
    "A chunk returned from vector search with metadata for citations."
    document_id:UUID
    filename:str
    page:int| None
    chunk_index:int
    context:str
    distance:float #0 = same direction and 1= opposite direction

async def vector_search(
    session:AsyncSession,
    tenant_id:UUID,
    question:str,
    top_k:int=20,
)->List[RetrievedChunk]:
    """
    Embeded the question and run cosine similarity search scoped to tenant. 

    Args:
        session: async database session.
        tenant_id: tenant ID.
        question: question to search for.
        top_k: number of results to return.
    
    Returns:
        List[RetrievedChunk]: list of retrieved chunks
    """
    # 1. Embed the question
    settings=get_settings()
    model=get_embedding_model()
    question_embedding=model.encode(
        [question],
        batch_size=1,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )[0].astype("float32")

    # 2. Cosine search wtih tenant filter inside the sql
    # JOIN documents to get fileaname; ORDER BY distance ASC (nearest first)
    stmt=(
        select(
            ChunkModel.document_id,
            Document.filename,
            ChunkModel.page,
            ChunkModel.chunk_index,
            ChunkModel.content,
            ChunkModel.embedding.cosine_distance(question_embedding).label("distance"),
        )
        .join(Document,ChunkModel.document_id==Document.id)
        .where(ChunkModel.tenant_id==tenant_id)
        .order_by(text("distance"))
        .limit(top_k)
    )
    result=await session.execute(stmt)
    rows=result.all()

    return[
        RetrievedChunk(
            document_id=row.document_id,
            filename=row.page,
            page=row.page,
            chunk_index=row.chunk_index,
            distance=row.distance,
        ) for  row in rows
    ]

# Line-by-line:
# Line	What it does
# @dataclass(frozen=True) -Immutable result object — safe to pass around.
# distance: float	-Cosine distance from pgvector (0 = perfect match).
# get_embedding_model()	-Reuses the cached model from ingestion (lru_cache).
# model.encode([...])[0]	-Embeds the single question; returns numpy array, take first.
# astype("float32")	-pgvector expects float32.
# ChunkModel.embedding.cosine_distance(...)	-SQLAlchemy-pgvector generates embedding <=> $1.
# .join(Document, ...)	-Gets filename for citations.
# .where(ChunkModel.tenant_id == tenant_id)	-Tenant filter inside SQL — critical for isolation.
# .order_by(text("distance"))	-Orders by the computed distance column (nearest first).
# .limit(top_k)	-Caps results (default 20 from settings).

# Python features:
# - cosine_distance() — SQLAlchemy-pgvector method that emits the <=> operator.
# - text("distance") — refers to the labeled column in ORDER BY.
# - result.all() — returns list of Row objects with named attributes.

# Chunk 3: Standalone search helper (for CLI / tests)
from app.db.session import AsyncSessionLocal

async def search_chunks(
    tenant_id: UUID,
    question: str,
    top_k:int=20,
    session_factory=AsyncSessionLocal,
)-> List[RetrievedChunk]:
    """
    Convenience: open session, run vector_search, close session.
    Used by CLI and tests. Accepts optional session_factory for test injection.
    """
    async with session_factory() as session:
        return await vector_search(session,tenant_id,question,top_k)

# Line-by-line:
# - AsyncSessionLocal — the same session factory used by ingestion (from app/db/session.py).
# - session_factory=AsyncSessionLocal — default argument lets tests inject a test session factory (e.g., AsyncTestSessionLocal from conftest.py).
# - async with session_factory() as session — opens session, runs query, commits/rollbacks automatically on exit.

# Why separate vector_search and search_chunks:
# - vector_search(session, ...) — pure function, easy to unit test with a mocked session.
# - search_chunks(...) — opens/closes session, used by CLI and integration tests.
