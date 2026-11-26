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


def _classify_error(e: Exception) -> str:
    """
    Classify exception and return a safe, user-friendly error message.
    No stack traces, no internal paths, no database details.
    """
    error_str = str(e).lower()
    
    # File not found / missing
    if isinstance(e, FileNotFoundError) or "not found" in error_str:
        return "Source file not found"
    
    # PDF specific errors
    if "not a valid pdf" in error_str or "missing %pdf" in error_str:
        return "Invalid PDF file (missing PDF header)"
    if "encrypted" in error_str or "password protected" in error_str:
        return "PDF is encrypted or password protected"
    if "empty" in error_str and "pdf" in error_str:
        return "PDF file is empty"
    if "scanned" in error_str and "no extractable text" in error_str:
        return "PDF appears to be scanned (no extractable text)"
    
    # Text encoding errors
    if "utf-8" in error_str or "unicode" in error_str or "decode" in error_str:
        return "File contains invalid UTF-8 encoding"
    
    # Database errors (should not leak details) - check BEFORE ollama/embedding
    if "database" in error_str or "connection pool" in error_str or "connection refused" in error_str:
        return "Database temporarily unavailable"
    
    # Ollama / embedding service errors
    if "ollama" in error_str or "embedding" in error_str or "connect" in error_str:
        return "Embedding service temporarily unavailable"
    if "timeout" in error_str:
        return "Embedding service timeout"
    
    # Permission errors
    if "permission" in error_str or "access denied" in error_str:
        return "File access denied"
    
    # Generic fallback - safe message
    return "Document processing failed"


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
        error = "Source file not found"
        async with AsyncSessionLocal() as session:
            await mark_document_failed(session, doc_id, error)
        return {"status": "failed", "error": error}

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Document.filename).where(Document.id == doc_id)
        )
        original_filename = result.scalar_one_or_none()

    if not original_filename:
        error = "Document not found in database"
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
        # Classify error and return safe message
        safe_error = _classify_error(e)
        async with AsyncSessionLocal() as session:
            await mark_document_failed(session, doc_id, safe_error)
        # No stack trace in result - safe for retries
        return {"status": "failed", "error": safe_error}