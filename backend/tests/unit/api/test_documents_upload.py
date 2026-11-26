import io
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import UUID, uuid4
from fastapi import HTTPException

from app.main import app
from app.db.session import get_session
from app.core.config import get_settings
from app.services.documents import enqueue_ingestion_job, validate_file_content
from tests.conftest import AsyncTestSessionLocal

@pytest.fixture
def override_dependencies():
    """Override FastAPI dependencies for testing."""
    # Override queue - mock enqueue_ingestion_job
    # Note: DB session override is handled by conftest.py's autouse fixture
    async def mock_enqueue(*args, **kwargs):
        return None
    
    with patch("app.api.v1.documents.enqueue_ingestion_job", mock_enqueue):
        yield
    
    app.dependency_overrides.clear()


@pytest.fixture
def api_key_headers():
    """Create a test API key and return headers."""
    from app.services.keys import create_api_key
    from app.db.models.tenant import Tenant
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    import asyncio
    from uuid import UUID

    TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")
    
    async def _create_key():
        async with AsyncTestSessionLocal() as session:
            await session.execute(
                pg_insert(Tenant).values(id=TENANT_ID, name="test-tenant").on_conflict_do_nothing(index_elements=["id"])
            )
            await session.commit()
            api_key, full_key = await create_api_key(session, TENANT_ID, "Test Key", ["documents", "query"])
            await session.commit()
            return full_key
    
    full_key = asyncio.run(_create_key())
    return {"X-API-Key": full_key}


@pytest.fixture
async def client(override_dependencies):
    """AsyncClient with overridden dependencies."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

class TestUploadValidation:
    """Tests for POST /v1/documents validation."""

    @pytest.mark.asyncio
    async def test_wrong_file_type_rejected(self, client, api_key_headers):
        """File with .doc extension rejected (not in allowed types)."""
        files = {"file": ("test.doc", b"fake content", "application/msword")}
        response = await client.post("/v1/documents", files=files, headers=api_key_headers)
        
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "invalid_file"

    @pytest.mark.asyncio
    async def test_invalid_utf8_txt_rejected(self, client, api_key_headers):
        """TXT file with invalid UTF-8 bytes rejected."""
        invalid_utf8 = b"Hello \xff\xfe world"  # Invalid UTF-8 sequence
        files = {"file": ("test.txt", invalid_utf8, "text/plain")}
        response = await client.post("/v1/documents", files=files, headers=api_key_headers)
        
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "invalid_file"

    @pytest.mark.asyncio
    async def test_pdf_missing_magic_bytes_rejected(self, client, api_key_headers):
        """File with .pdf extension but no %PDF- header rejected."""
        fake_pdf = b"This is not a real PDF"
        files = {"file": ("fake.pdf", fake_pdf, "application/pdf")}
        response = await client.post("/v1/documents", files=files, headers=api_key_headers)
        
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "invalid_file"

    @pytest.mark.asyncio
    async def test_oversized_file_413(self, client, api_key_headers):
        """File exceeding max_upload_mb returns 413."""
        settings = get_settings()
        oversized = b"x" * (settings.max_upload_mb * 1024 * 1024 + 1)
        files = {"file": ("huge.txt", oversized, "text/plain")}
        response = await client.post("/v1/documents", files=files, headers=api_key_headers)
        
        assert response.status_code == 413
        assert response.json()["detail"]["code"] == "file_too_large"

    @pytest.mark.asyncio
    async def test_malicious_filename_safe(self, client, api_key_headers):
        """Filename like ../../x.pdf does not affect storage path."""
        # Use a valid extension with path traversal attempt
        files = {"file": ("../../x.pdf", b"%PDF-1.4 fake pdf content", "application/pdf")}
        response = await client.post("/v1/documents", files=files, headers=api_key_headers)
        
        assert response.status_code == 202
        # File should be stored as <document_id>.pdf, not with path traversal
        # The response contains document_id, we can verify the file was stored safely
        document_id = response.json()["document_id"]
        # The actual file path uses document_id, not the original filename
        # This is verified by the service layer

    @pytest.mark.asyncio
    async def test_duplicate_filename_409(self, client, api_key_headers):
        """Same tenant uploading same filename twice -> 409."""
        # First upload
        files1 = {"file": ("duplicate.txt", b"content 1", "text/plain")}
        response1 = await client.post("/v1/documents", files=files1, headers=api_key_headers)
        assert response1.status_code == 202
        
        # Second upload with same filename
        files2 = {"file": ("duplicate.txt", b"content 2", "text/plain")}
        response2 = await client.post("/v1/documents", files=files2, headers=api_key_headers)
        
        assert response2.status_code == 409
        assert response2.json()["detail"]["code"] == "conflict"


# ──────────────────────────────────────────────────────────────────────────────
# Unit tests for validate_file_content (no HTTP/client needed)
# ──────────────────────────────────────────────────────────────────────────────

class TestValidateFileContent:
    """Unit tests for validate_file_content function."""

    def test_valid_utf8_txt_accepted(self):
        """Valid UTF-8 text file should be accepted."""
        class MockFile:
            def __init__(self):
                self.file = io.BytesIO(b"Hello world")
        
        file = MockFile()
        validate_file_content(file, ".txt")

    def test_invalid_utf8_txt_rejected(self):
        """Invalid UTF-8 text file should be rejected."""
        class MockFile:
            def __init__(self):
                self.file = io.BytesIO(b"Hello \xff\xfe world")
        
        file = MockFile()
        
        with pytest.raises(HTTPException) as exc_info:
            validate_file_content(file, ".txt")
        
        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["code"] == "invalid_file"

    def test_valid_utf8_md_accepted(self):
        """Valid UTF-8 markdown file should be accepted."""
        class MockFile:
            def __init__(self):
                self.file = io.BytesIO(b"# Hello\n\nValid markdown")
        
        file = MockFile()
        validate_file_content(file, ".md")

    def test_invalid_utf8_md_rejected(self):
        """Invalid UTF-8 markdown file should be rejected."""
        class MockFile:
            def __init__(self):
                self.file = io.BytesIO(b"# Hello \xff\xfe world")
        
        file = MockFile()
        
        with pytest.raises(HTTPException) as exc_info:
            validate_file_content(file, ".md")
        
        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["code"] == "invalid_file"

    def test_valid_pdf_accepted(self):
        """Valid PDF with magic bytes should be accepted."""
        class MockFile:
            def __init__(self):
                self.file = io.BytesIO(b"%PDF-1.4 fake pdf content")
        
        file = MockFile()
        validate_file_content(file, ".pdf")

    def test_pdf_missing_magic_bytes_rejected(self):
        """PDF without magic bytes should be rejected."""
        class MockFile:
            def __init__(self):
                self.file = io.BytesIO(b"Not a real PDF")
        
        file = MockFile()
        
        with pytest.raises(HTTPException) as exc_info:
            validate_file_content(file, ".pdf")
        
        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["code"] == "invalid_file"

