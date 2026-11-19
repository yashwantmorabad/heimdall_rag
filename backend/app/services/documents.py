"Document service: file storage, DB operations, job enqueue."

import os
import shutil
from pathlib import Path
from uuid import UUID, uuid4
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile, HTTPException, status

from app.db.models.document import Document
from app.core.config import get_settings
from app.core.queue import get_redis_pool

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}
PDF_MAGIC = b"%PDF-"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

def validate_file_content(file: UploadFile, ext: str) -> None:
    """
    Validate the content of the uploaded file based on its extension.
    Raises HTTPException if the content is invalid.
    """
    # Read first chunk for validation
    chunk = file.file.read(8192)
    file.file.seek(0)  # Reset file pointer after reading

    if ext == ".pdf":
        if not chunk.startswith(PDF_MAGIC):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "invalid_file", "message": "Uploaded PDF file is invalid."},
            )
        elif ext in {".txt", ".md"}:
            try:
                chunk.decode("utf-8")
            except UnicodeDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={"code": "invalid_file", "message": f"Uploaded {ext} file is not valid UTF-8."},
                )

async def save_uploaded_file(
        file: UploadFile,
        tenant_id: UUID,
        document_id: UUID,
        ext: str,
) -> Path:
    """
    Save uploaded file to STORAGE_PATH/tenant_id/document_id.ext.
    Returns the saved file path.
    """
    settings = get_settings()
    storage_root = Path(settings.storage_path).resolve()
    tenant_dir = storage_root / str(tenant_id)
    tenant_dir.mkdir(parents=True, exist_ok=True)

    saved_path = tenant_dir / f"{document_id}{ext}"

    # Write file
    with saved_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    return saved_path
async def create_document_record(
        session: AsyncSession,
        tenant_id: UUID,
        document_id: UUID,
        original_filename: str,
        saved_path: Path,
) -> Document:
    """
    Create document row with status= 'queued'.
    Raises 409 if same tenant already has this failure.
    """
    # Check for duplicate filename(unique constraint on tenant_id + filename)
    result = await seesion.execute(
        select(Document.id).where(
            Document.tenant_id == tenant_id,
            Document.filename == original_filename,
        ))

    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "conflict", "message": f"Document '{original_filename}' already exists"},
        )

    doc = Document(
        id=document_id,
        tenant_id=tenant_id,
        fileaname=original_filename,
        status="queued",
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)
    return doc

async def enqueue_ingestion_job(document_id: UUID, tenant_id: UUID) -> None:
    "Enqueue the ingestion job to arc/redis."
    try:
        reids = await get_redis_pool()
        await redis.enqueue_job("ingest_document", document_id=str(document_id), tenant_id=str(tenant_id))
    except Exception as e:
        # Redis unavailable or enqueue failed
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "service_unavailable", "message": "Failed to queue document for processing"},
        ) from e

async def mark_document_failed(session: AsyncSession, document_id: UUID, error: str) -> None:
    """Mark document as failed with error message."""
    from sqlalchemy import update
    await session.execute(
        update(Document)
        .where(Document.id == document_id)
        .values(status="failed", error=error)
    )
    await session.commit()

async def  list_documents(
        session: AsyncSession,
        tenant_id: UUID,
        limit: int = 50,
        offset: int = 0,
) -> list[Document]:
    from sqlalchemy import select
    result = await session.execute(
        select(Document)
        .where(Document.tenant_id == tenant_id)
        .order_by(Document.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()

async def get_document(
        session: AsyncSession,
        tenant_id: UUID,
        document_id: UUID,
) -> Document | None:
    from sqlalchemy import select
    result = await session.execute(
        select(Document).where(
            Document.id == document_id,
            Document.tenant_id == tenant_id
        )
    )
    return result.scalar_one_or_none()
async def delete_document(
    session: AsyncSession,
    tenant_id: UUID,
    document_id: UUID,
    storage_path: Path,
) -> bool:
    """
    Delete a document, its chunks, and the stored file.
    Returns True if deleted, False if not found.
    """
    from sqlalchemy import delete, select
    from app.db.models.chunk import Chunk as ChunkModel

    # Find document (tenant-scoped)
    doc = await get_document(session, tenant_id, document_id)
    if not doc:
        return False

    # Delete chunks first (FK constraint)
    await session.execute(
        delete(ChunkModel).where(ChunkModel.document_id == document_id)
    )

    # Delete document row
    await session.execute(
        delete(Document).where(Document.id == document_id)
    )
    await session.commit()

    # Delete stored file
    for ext in (".pdf", ".txt", ".md"):
        file_path = storage_path / str(tenant_id) / f"{document_id}{ext}"
        if file_path.exists():
            file_path.unlink(missing_ok=True)
            break

    return True