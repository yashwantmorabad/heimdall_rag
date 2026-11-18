"Document endpoints: upload, list, get, delete."

from uuid import UUID
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_api_key, require_scope, get_tenant_id, get_redis_pool, get_session
from app.services.documents import(
    validate_file_content,
    save_uploaded_file,
    create_document_record,
    enqueue_ingestion_job,
    mark_document_failed,
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

    # Vaildate filename
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

    # Validate file size (FastAPI reads into memory for small files, but we check content-length)
    content_length = file.headers.get("content-length")
    if content_length and int(content_length) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"code": "file_too_large", "message": f"File exceeds {settings.max_upload_mb} MB limit"},
        )

    # Validate content matches extension
    validate_file_content(file, ext)

    # Generate document ID and save file
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


# Placeholder for GET/DELETE (Piece 5)
@router.get("/documents")
async def list_documents():
    return {"documents": []}


@router.get("/documents/{document_id}")
async def get_document(document_id: UUID):
    return {"document_id": str(document_id)}


@router.delete("/documents/{document_id}")
async def delete_document(document_id: UUID):
    return {"deleted": True}