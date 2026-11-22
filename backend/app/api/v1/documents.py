from uuid import UUID
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Query

from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path

from app.api.deps import get_api_key, require_scope, get_tenant_id, get_session
from app.services.documents import (
    validate_file_content,
    save_uploaded_file,
    create_document_record,
    enqueue_ingestion_job,
    mark_document_failed,
    get_document,
    delete_document,
    list_documents,
)
from app.db.models.document import Document
from app.core.config import get_settings

router = APIRouter()

@router.post(
    "/documents",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_scope("documents"))],
)
async def upload_document(
    file: UploadFile = File(...),
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """
    Upload a document for processing.

    - Validates file type (pdf, txt, md) by content and extension
    - Enforces max file size
    - Saves file to storage
    - Creates document row with status='queued'
    - Enqueues ingestion job
    - Returns 202 with document_id and status
    """
    settings = get_settings()
    max_size = settings.max_upload_mb * 1024 * 1024  # Convert MB to bytes

    # Vaidate file name 
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_file", "message": "Filename is required"},
        )

    ext = Path(file.filename).suffix.lower()
    if ext not in {".pdf", ".txt", ".md"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_file", "message": f"Unsupported file type: {ext}. Allowed: .pdf, .txt, .md"},
        )
    content_length = file.headers.get("content-length")
    if content_length and int(content_length) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"code": "file_too_large", "message": f"File exceeds {settings.max_upload_mb} MB limit"},
        )

    # Validate content matches extension
    validate_file_content(file, ext)

    # Generate document ID and save file
    from uuid import uuid4
    document_id = UUID(str(uuid4()))
    saved_path = None

    try:
        saved_path = await save_uploaded_file(file, tenant_id, document_id, ext)

        # Create document record
        await create_document_record(session, tenant_id, document_id, file.filename, saved_path)

        # Enqueue ingestion job
        await enqueue_ingestion_job(document_id, tenant_id)

        return {"document_id": str(document_id), "status": "queued"}

    except HTTPException:
        # Clean up saved file on any HTTP error (409, 503, etc.)
        if saved_path and saved_path.exists():
            saved_path.unlink(missing_ok=True)
        raise

    except Exception as e:
        # Unexpected error: clean up and return 500
        if saved_path and saved_path.exists():
            saved_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "internal_error", "message": "Failed to process upload"},
        ) from e


@router.get(
    "/documents",
    dependencies=[Depends(require_scope("documents"))],
)
async def list_documents_endpoint(
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List documents for the authenticated tenant."""
    docs = await list_documents(session, tenant_id, limit, offset)
    return {
        "documents": [
            {
                "document_id": str(d.id),
                "filename": d.filename,
                "status": d.status,
                "error": d.error,
                "created_at": d.created_at.isoformat(),
            }
            for d in docs
        ],
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/documents/{document_id}",
    dependencies=[Depends(require_scope("documents"))],
)
async def get_document_endpoint(
    document_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Get a single document by ID (tenant-scoped). Returns 404 if not found."""
    doc = await get_document(session, tenant_id, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Document not found"},
        )
    return {
        "document_id": str(doc.id),
        "filename": doc.filename,
        "status": doc.status,
        "error": doc.error,
        "created_at": doc.created_at.isoformat(),
    }


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_scope("documents"))],
)
async def delete_document_endpoint(
    document_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Delete a document, its chunks, and the stored file. Returns 404 if not found."""
    settings = get_settings()
    storage_root = Path(settings.storage_path).resolve()

    deleted = await delete_document(session, tenant_id, document_id, storage_root)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Document not found"},
        )