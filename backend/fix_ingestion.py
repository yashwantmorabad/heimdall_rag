import re

with open('app/workers/ingestion.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the position after 'from app.core.config import get_settings\n\nasync def ingest_document'
old = 'from app.core.config import get_settings\n\nasync def ingest_document'
new = '''from app.core.config import get_settings


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
    
    # Ollama / embedding service errors
    if "ollama" in error_str or "embedding" in error_str or "connect" in error_str:
        return "Embedding service temporarily unavailable"
    if "timeout" in error_str:
        return "Embedding service timeout"
    
    # Database errors (should not leak details)
    if "database" in error_str or "connection" in error_str:
        return "Database temporarily unavailable"
    
    # Permission errors
    if "permission" in error_str or "access denied" in error_str:
        return "File access denied"
    
    # Generic fallback - safe message
    return "Document processing failed"


async def ingest_document'''

content = content.replace('from app.core.config import get_settings\n\nasync def ingest_document', new)

with open('app/workers/ingestion.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done')