"Document parsers for PDF, TXT, MD files."

from dataclasses import dataclass
from pathlib import Path
from typing import List

import fitz #PyMuPDF: is used for PDF parsing

@dataclass(frozen=True)
class ParsedPage:
    """A single page of extracted text with its page number (1-indexed)."""
    page_number: int
    text: str

def parse_pdf(file_path: Path) -> List[ParsedPage]:
    """
    Extract text from a PDF, one page at a time.

    Validates:
    - File exists and is readable
    - Magic bytes
    - Not encrypted
    - Not empty
    - Not scanned-only 

    Args:
        file_path: Path to the PDF file
        
    Returns:
        A list of ParsedPage (page_number starts at 1).

    Raises:
        ValueError: If the file is not a PDF or invalid file.
        FileNotFoundError: If the file does not exist.
    """

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with file_path.open("rb") as f:
        header=f.read(5)
        if header!=b"%PDF-":
            raise ValueError(f"Not a valid PDF (missing %PDF- header): {file_path}")

    doc=fitz.open(file_path)

    try:
        #check encryption
        if doc.is_encrypted:
            raise ValueError(f"PDF is encrypted (password protected): {file_path}")
        
        #checking pages count
        if doc.page_count == 0:
            raise ValueError(f"PDF is empty: {file_path}")
        
        pages: List[ParsedPage] = []
        for page_num in range(doc.page_count):
            page= doc[page_num]
            text=page.get_text("text")

            if text:
                pages.append(ParsedPage(page_number=page_num +1,text=text))
        
        if not pages:
            raise ValueError(f"PDF appears to be scanned (no extractable text): {file_path}")

        return pages

    finally:
        doc.close()

def parse_txt(file_path: Path) -> List[ParsedPage]:
    """
    Read a plain text file as UTF-8.

    Args:
        file_path: Path to the .txt file.

    Returns:
        Single-item list with page_number=1 (text files have no pages).

    Raises:
        ValueError: If file is not valid UTF-8.
        FileNotFoundError: If file doesn't exist.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        text=file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        raise ValueError(f"File is not valid UTF-8: {file_path}") from e

    if not text.strip():
        #Empty or whitespace-only file - return empty list(caller decises what to do)
        return []
    
    return [ParsedPage(page_number=1,text=text)]

def parse_markdown(file_path: Path) -> List[ParsedPage]:
    """
    Read a Markdown file as UTF-8.

    Same as TXT for now — structure-aware chunking happens later.

    Args:
        file_path: Path to the .md/.markdown file.

    Returns:
        Single-item list with page_number=1.

    Raises:
        ValueError: If file is not valid UTF-8.
        FileNotFoundError: If file doesn't exist.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
        
    try:
        text=file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        raise ValueError(f"File is not valid UTF-8: {file_path}") from e
    
    if not text.strip():
        #Empty or whitespace-only file - return empty list(caller decises what to do)
        return []
    
    return [ParsedPage(page_number=1,text=text)]

_PARSERS={
    ".pdf":parse_pdf,
    ".txt":parse_txt,
    ".md":parse_markdown,
    ".markdown":parse_markdown
}

def parse_file(file_path: Path) -> List[ParsedPage]:
    """
    Dispatch to the right parser based on file extension.

    Args:
        file_path: Path to the document.

    Returns:
        List of ParsedPage objects.

    Raises:
        ValueError: For unknown file types.
        FileNotFoundError: If file doesn't exist.
    """
    suffix = file_path.suffix.lower()
    parser = _PARSERS.get(suffix)
    if parser is None:
        supported = ", ".join(sorted(_PARSERS.keys()))
        raise ValueError(f"Unsupported file type {suffix}. Supported: {supported}")
    
    return parser(file_path)