"""Tests for worker ingestion failure handling - focused on error classification logic."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import UUID, uuid4
from pathlib import Path

# Skip tests if PyMuPDF not available (Windows App Control policy)
try:
    import fitz
    PYMUPDF_AVAILABLE = True
except (ImportError, ModuleNotFoundError, OSError):
    PYMUPDF_AVAILABLE = False

if PYMUPDF_AVAILABLE:
    from app.workers.ingestion import ingest_document, _classify_error
    from tests.conftest import AsyncTestSessionLocal
    from app.db.models.document import Document
    from app.db.models.tenant import Tenant
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy import select
else:
    # Mock imports for test collection
    ingest_document = None
    AsyncTestSessionLocal = None
    Document = None
    Tenant = None
    pg_insert = None
    select = None

from unittest.mock import AsyncMock, patch, MagicMock
from uuid import UUID, uuid4
from pathlib import Path
import io
import pytest


# Skip all tests if PyMuPDF not available
pytestmark = pytest.mark.skipif(not PYMUPDF_AVAILABLE, reason="PyMuPDF not available (Windows App Control policy)")


# ──────────────────────────────────────────────────────────────────────────────
# Tests for _classify_error function (no DB needed)
# ──────────────────────────────────────────────────────────────────────────────

class TestClassifyError:
    """Tests for the _classify_error function - no DB needed."""

    def test_file_not_found(self):
        """FileNotFoundError should return safe message."""
        e = FileNotFoundError("File not found")
        result = _classify_error(e)
        assert result == "Source file not found"

    def test_not_found_string(self):
        """String containing 'not found' should return safe message."""
        e = Exception("File not found at path")
        result = _classify_error(e)
        assert result == "Source file not found"

    def test_invalid_pdf_missing_header(self):
        """PDF missing magic bytes should return safe message."""
        e = ValueError("Not a valid PDF (missing %PDF- header)")
        result = _classify_error(e)
        assert result == "Invalid PDF file (missing PDF header)"

    def test_encrypted_pdf(self):
        """Encrypted PDF should return safe message."""
        e = ValueError("PDF is encrypted (password protected)")
        result = _classify_error(e)
        assert result == "PDF is encrypted or password protected"

    def test_empty_pdf(self):
        """Empty PDF should return safe message."""
        e = ValueError("PDF is empty")
        result = _classify_error(e)
        assert result == "PDF file is empty"

    def test_scanned_pdf(self):
        """Scanned PDF should return safe message."""
        e = ValueError("PDF appears to be scanned (no extractable text)")
        result = _classify_error(e)
        assert result == "PDF appears to be scanned (no extractable text)"

    def test_invalid_utf8(self):
        """Invalid UTF-8 should return safe message."""
        e = UnicodeDecodeError("utf-8", b"", 0, 1, "invalid start byte")
        result = _classify_error(e)
        assert result == "File contains invalid UTF-8 encoding"

    def test_utf8_string(self):
        """String containing 'utf-8' should return encoding error."""
        e = Exception("utf-8 codec can't decode byte")
        result = _classify_error(e)
        assert result == "File contains invalid UTF-8 encoding"

    def test_unicode_string(self):
        """String containing 'unicode' should return encoding error."""
        e = Exception("unicode decode error")
        result = _classify_error(e)
        assert result == "File contains invalid UTF-8 encoding"

    def test_decode_string(self):
        """String containing 'decode' should return encoding error."""
        e = Exception("decode error")
        result = _classify_error(e)
        assert result == "File contains invalid UTF-8 encoding"

    def test_ollama_unavailable(self):
        """Ollama connection error should return safe message."""
        e = Exception("Cannot connect to ollama")
        result = _classify_error(e)
        assert result == "Embedding service temporarily unavailable"

    def test_embedding_service(self):
        """Embedding service error should return safe message."""
        e = Exception("embedding service failed")
        result = _classify_error(e)
        assert result == "Embedding service temporarily unavailable"

    def test_connection_error(self):
        """Connection error should return safe message (database connection)."""
        e = Exception("connection refused")
        result = _classify_error(e)
        assert result == "Database temporarily unavailable"

    def test_timeout_error(self):
        """Timeout should return safe message."""
        e = Exception("timeout")
        result = _classify_error(e)
        assert result == "Embedding service timeout"

    def test_database_error(self):
        """Database error should return safe message."""
        e = Exception("database connection failed")
        result = _classify_error(e)
        assert result == "Database temporarily unavailable"

    def test_connection_error_db(self):
        """Database connection error should return safe message."""
        e = Exception("connection pool exhausted")
        result = _classify_error(e)
        assert result == "Database temporarily unavailable"

    def test_permission_error(self):
        """Permission error should return safe message."""
        e = Exception("permission denied")
        result = _classify_error(e)
        assert result == "File access denied"

    def test_access_denied(self):
        """Access denied should return safe message."""
        e = Exception("access denied")
        result = _classify_error(e)
        assert result == "File access denied"

    def test_unknown_error(self):
        """Unknown error should return generic safe message."""
        e = Exception("Some random error")
        result = _classify_error(e)
        assert result == "Document processing failed"

    def test_case_insensitive(self):
        """Error classification should be case insensitive."""
        e = Exception("FILE NOT FOUND")
        result = _classify_error(e)
        assert result == "Source file not found"

    def test_partial_match(self):
        """Partial string matches should work."""
        e = Exception("The file was not found on disk")
        result = _classify_error(e)
        assert result == "Source file not found"