"Test for document parsers"

import tempfile
from pathlib import Path

import pytest

from app.rag.ingestion.parsers import parse_file, parse_pdf, parse_txt,parse_markdown, ParsedPage

#Fixtures: create real temporary files

@pytest.fixture
def sample_pdf_path(tmp_path):
    """Create a simple 2-page PDF using PyMuPDF."""
    import fitz
    doc = fitz.open()
    page1 = doc.new_page()
    page1.insert_text((72, 72), "Page one content")
    page2 = doc.new_page()
    page2.insert_text((72, 72), "Page two content")
    
    file_path = tmp_path / "sample.pdf"
    doc.save(str(file_path))  # fitz needs string path on Windows
    doc.close()
    return file_path

@pytest.fixture
def sample_txt_path(tmp_path):
    """Create a simple text file."""
    file_path = tmp_path / "sample.txt"
    file_path.write_text("Hello text file", encoding="utf-8")
    return file_path


@pytest.fixture
def sample_md_path(tmp_path):
    """Create a simple markdown file."""
    file_path = tmp_path / "sample.md"
    file_path.write_text("# Heading\n\nMarkdown content", encoding="utf-8")
    return file_path

def test_parse_pdf_returns_pages(sample_pdf_path):
    """PDF parser returns a list of pages."""
    pages=parse_pdf(sample_pdf_path)

    assert len(pages)==2
    assert pages[0].page_number==1
    assert "Page one content" in pages[0].text
    assert pages[1].page_number==2
    assert "Page two content" in pages[1].text
    
def test_parse_pdf_rejects_missing_files():
    "Missing file raises FileNotFoundError"
    with pytest.raises(FileNotFoundError):
        parse_pdf(Path("nonexistent.pdf"))
    
def test_parse_pdf_rejects_non_pdf(tmp_path):
    "File without %PDF- header raises ValueError"
    fake=tmp_path / "fake.pdf"
    fake.write_text("not a pdf")
    with pytest.raises(ValueError, match="Not a valid PDF"):
        parse_pdf(fake)
    
def test_parse_txt_returns_single_page(sample_txt_path):
    """TXT parser returns a single page."""
    pages=parse_txt(sample_txt_path)

    assert len(pages)==1
    assert pages[0].page_number==1
    assert pages[0].text=="Hello text file"

def test_parse_markdown_returns_single_page(sample_md_path):
    """Markdown parser returns single page with page_number=1."""
    pages = parse_markdown(sample_md_path)

    assert len(pages) == 1
    assert pages[0].page_number == 1
    assert "# Heading" in pages[0].text


def test_parse_file_dispatches_by_extension(sample_pdf_path, sample_txt_path, sample_md_path):
    """parse_file routes to correct parser based on extension."""
    assert len(parse_file(sample_pdf_path)) == 2
    assert len(parse_file(sample_txt_path)) == 1
    assert len(parse_file(sample_md_path)) == 1


def test_parse_file_rejects_unsupported_extension(tmp_path):
    """Unsupported extension raises ValueError with helpful message."""
    weird = tmp_path / "file.xyz"
    weird.write_text("content")
    with pytest.raises(ValueError, match="Unsupported file type"):
        parse_file(weird)


def test_parse_txt_rejects_invalid_utf8(tmp_path):
    """Non-UTF-8 file raises ValueError."""
    bad = tmp_path / "bad.txt"
    bad.write_bytes(b"\xff\xfe")  # Invalid UTF-8
    with pytest.raises(ValueError, match="not valid UTF-8"):
        parse_txt(bad)
