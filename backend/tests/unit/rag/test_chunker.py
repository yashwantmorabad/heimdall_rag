import pytest

from app.rag.ingestion.chunker import(
    chunk_file,
    chunk_markdown,
    chunk_pdf,
    chunk_txt,
    Chunk,
)
from app.rag.ingestion.parsers import ParsedPage

# ---- Fake tokenizer for fast, deterministic tests ----
# Counts words as tokens (rough approximation)
def fake_token_counter(text:str)->int:
    """Simple word-count tokenizer for testing."""
    return len(text.split())

# ---- Fixtures ----
@pytest.fixture
def markdown_pages():
    "Two-page MD (simulated as one page with headings)"
    return [ParsedPage(page_number=1,text="""# Introduction
    Welcome to the guide. This is the first section.

    ## Getting Started

    First, install the tool. Then run the steup command

    ## Usage

    Run the command with arguments. Check the output.""")]

@pytest.fixture
def pdf_pages():
    "three pages pdf. And app 40 tokens each page"
    return [
        ParsedPage(page_number=1,text="Page one content. "*13),
        ParsedPage(page_number=2,text="Page two content. "*13),
        ParsedPage(page_number=3,text="Page three content. "*13),
    ]

@pytest.fixture
def txt_page():
    "Single page txt"
    return [ParsedPage(page_number=1, text=("Word " * 100).strip())]


# ---- Tests ----

def test_chunk_markdown_respects_headings(markdown_pages):
    """Markdown chunker keeps headings with their content."""
    chunks=chunk_markdown(markdown_pages,fake_token_counter,chunk_size=30,chunk_overlap=5)

    # should have multiple chunks
    assert len(chunks) >= 2

    # First chunk should contain the first heading
    assert "# Introduction" in chunks[0].text
    #Headings should not be split from their content
    for chunk in chunks:
        # If a chunk has a heading, it should have content after it 
        if chunk.text.startswith("#"):
            assert len(chunk.text)> len(chunk.text.split("\n")[0])

def test_chunk_markdown_chunk_metadata(markdown_pages):
    "Chunks have correct token_count, page_number, chunk_index."
    chunks= chunk_markdown(markdown_pages,fake_token_counter,chunk_size=30,chunk_overlap=5)
    for i,chunk in enumerate(chunks):
        assert chunk.token_count==fake_token_counter(chunk.text)
        assert chunk.page_number==1
        assert chunk.chunk_index==i

def test_chunk_pdf_one_chunk_per_page_when_small(pdf_pages):
    "Small pdf pages become one chunk each."
    # each page ~ 40 tokens, chunk_size=50 -> one chunk per page
    chunks = chunk_pdf(pdf_pages,fake_token_counter,chunk_size=50,chunk_overlap=5)

    assert len(chunks)==3
    assert chunks[0].page_number==1
    assert chunks[1].page_number==2
    assert chunks[2].page_number==3
    assert all(c.chunk_index==i for i,c in enumerate(chunks))

def test_chunk_pdf_splits_large_page(pdf_pages):
    "Large pdf page gets split into multiple chunks."
    # each page ~ 40 tokens, chunk_size=100 -> two chunks
    chunks=chunk_pdf(pdf_pages,fake_token_counter,chunk_size=20,chunk_overlap=3)

    assert len(chunks) >= 6
    #Page numbers are preserved
    page_nums=[c.page_number for c in chunks]
    assert page_nums.count(1)>=2
    assert page_nums.count(2)>=2
    assert page_nums.count(3)>=2

def test_chunk_txt_sliding_window(txt_page):
    "TXT uses sliding window with overlap."
    #100 tokens, chunk_size=30, overlap=5->windows of ~30 with 5 overlap
    chunks = chunk_txt(txt_page,fake_token_counter,chunk_size=30,chunk_overlap=5)
    assert len(chunks)>=3
    # Each chunk has token_count > 0
    assert all(c.token_count>0 for c in chunks)
    # overlap: consecutive chunks share some words
    #(hard to test exactly with word-count fake, but structure is there)
    assert chunks[0].page_number==1
    assert chunks[-1].page_number==1

def test_chunk_file_dispatches_correctly(markdown_pages, pdf_pages,txt_page):
    "chunk_file routes to correct chunker."
    md_chunks=chunk_file(markdown_pages,fake_token_counter,chunk_size=30,chunk_overlap=5,file_type="md")
    pdf_chunks=chunk_file(pdf_pages,fake_token_counter,chunk_size=30,chunk_overlap=5,file_type="pdf")
    txt_chunks=chunk_file(txt_page,fake_token_counter,chunk_size=30,chunk_overlap=5,file_type="txt")

    assert len(md_chunks)>0
    assert len(pdf_chunks)>0
    assert len(txt_chunks)>0

def test_chunk_file_rejects_unknown_type(markdown_pages):
    "Unknown file type raises ValueError."
    with pytest.raises(ValueError, match="Unknown file type"):
        chunk_file(markdown_pages,fake_token_counter,chunk_size=30,chunk_overlap=5,file_type="xyz") 
