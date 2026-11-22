"arq job: document ingestion."

from uuid import UUID
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.db.models.document import Document
from app.rag.ingestion.pipeline import ingest_file
from app.services.documents import mark_document_failed
from app.core.config import get_settings

async def ingest_document(ctx, document_id: str, tenant_id: str) -> dict:
    """
    arq job to ingest a document.

    Args:
        ctx: arq context (contains redis, etc.)
        document_id: Document UUID as string
        tenant_id: Tenant UUID as string

    Returns:
        Dict with status for arq result tracking
    """
    doc_id = UUID(document_id)
    tenant_uuid = UUID(tenant_id)
    settings = get_settings()

    storage_root = Path(settings.storage_path).resolve()
    tenant_dir = storage_root / str(tenant_uuid)

    file_path = None
    for ext in (".pdf", ".txt",".md"):
        candidate = tenant_dir / f"{doc_id}{ext}"
        if candidate.exists():
            file_path = candidate
            break

    if not file_path:
        error = f"Source file not found for the document {doc_id} "
        async with AsyncSessionLocal() as session:
            await mark_document_failed(session, doc_id, error)
        return {"status": "failed", "error": error}

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Document.filename).where(Document.id == doc_id)
        )
        original_filename = result.scalar_one_or_none()

    if not original_filename:
        error = f"Document {doc_id} not found in database"
        async with AsyncSessionLocal() as session:
            await mark_document_failed(session, doc_id, error)
        return {"status": "failed", "error": error}

    try:
        async with AsyncSessionLocal() as session:
            pass

        chunk_stored = await ingest_file(
            file_path=file_path,
            tenant_id=tenant_uuid,
            document_id=doc_id,
            original_filename=original_filename,
            session_factory=AsyncSessionLocal,
        )

        return {"status": "ready", "chunks_stored": chunk_stored}
    except Exception as e:
        error = f"Ingestion failed: {str(e)}"
        async with AsyncSessionLocal() as session:
            await mark_document_failed(session, doc_id, error)
        # No stack trace in result - safe for retries
        return {"status": "failed", "error": error}