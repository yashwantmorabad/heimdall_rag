"Ingestion pipeline: parse->clean->chunk->embed->store"

from app.rag.ingestion.embedder import ChunkDataclass
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.ingestion.parsers import parse_file,ParsedPage
from app.rag.ingestion.cleaner import clean_text
from app.rag.ingestion.chunker import chunk_file
from app.rag.ingestion.embedder import embed_chunks
from app.rag.ingestion.store import store_chunks
from app.db.session import AsyncSessionLocal

async def ingest_file(
    file_path: Path,
    tenant_id: UUID,
    document_id: UUID | None = None,
)->int:
    """
    Run the full ingestion pipline for a single file.

    Args:
        file_path: path to the document,
        tenant_id: Tenant UUID (for isolation).
        document_id: Optional document UUID (generated if not provided).

    Returns:
        Number of chunks stored (0 if already ingested or empty)
    """
    if document_id is None:
        document_id=uuid4()

    # 1. Parse
    pages: list[ParsedPage]=parse_file(file_path)

    # 2. Clean(per page)
    cleaned_pages=[
        ParsedPage(page_number=p.page_number, text=clean_text(p.text))
        for p in pages
    ]

    # 3. chunk
    file_type=file_path.suffix.lower().lstrip(".")
    chunks: list[ChunkDataclass]=chunk_file(
        cleaned_pages,
        token_counter=lambda t: len(t.split()),
        chunk_size=500,
        chunk_overlap=75,
        file_type=file_type,
    )

    # 4. Embed (loads model, computes embeddings)
    chunks=embed_chunks(chunks)

    # 5. Store
    async with AsyncSessionLocal() as session:
        stored= await store_chunks(session,tenant_id,document_id,chunks)

    return stored


# Line-by-line explanation
#Line(s): What it does
# document_id = uuid4(): Generate new document ID if not provided (for new uploads)
# parse_file(file_path): Dispatches to PDF/TXT/MD parser
# clean_text(p.text): Clean each page's text
# chunk_file(...): Dispatches to format-specific chunker. Uses fake token counter here (real one in embedder)
# embed_chunks(chunks): Loads model, computes embeddings, attaches to chunks
# AsyncSessionLocal(): Creates DB session (context manager = auto close)
# store_chunks(...): Idempotent insert with ON CONFLICT DO NOTHING

# Key Python features for beginners
# 1. UUID | None — Union type (Python 3.10+). Means "UUID or None".
# 2. List comprehensions — [ParsedPage(...) for p in pages] transforms each page.
# 3. lambda t: len(t.split()) — Anonymous function for token counting. Placeholder here; embedder uses real tokenizer.
# 4. async with — Async context manager. Ensures session closes even on error.
# 5. Pipeline function — Pure orchestration: calls each step in order, passes data forward. No business logic here.
