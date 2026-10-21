"Structure-aware text chunking for document ingestion"
import re
from dataclasses import dataclass
from typing import Callable, List

from app.rag.ingestion.parsers import ParsedPage

@dataclass(frozen=True)
class Chunk:
    "A chunk a text with metadata fro embeddings and storage"
    text:str
    token_count: int
    page_number: int
    #position of this chunk within it's page(0,1,2...)
    chunk_index: int
    #Embeddings vector (for LLM consumption)
    embedding:list[float] | None =None
    #Model used for embedding
    embedding_model: str | None = None

#Regex to split on MD headings (like #h1,h2## etc.)
#keeps the heading with the content that follows it.
_HEADING_RE=re.compile(r"^(#{1,6}\s+.+)$", re.MULTILINE)


def chunk_markdown(
    pages:list[ParsedPage],
    token_counter:Callable[[str],int],
    chunk_size:int,
    chunk_overlap:int,
) -> List[Chunk]:
    """
    Split MD text into chunks, respecting headings boundaries.

    Strategy:
    1. Join all pages with a page separator.
    2. split on headings (keeping headings).
    3. Pack selections into chunks of ~chunk_size tokens.
    4. Add overlap by including tail of previous chunk.

    Args:
        pages: Parsed pages from the markdown file (usually 1 page).
        token_counter: Function that returns token count for a string.
        chunk_size: Target tokens per chunk (from settings).
        chunk_overlap: Tokens to overlap between chunks (from settings).

    Returns:
        List of Chunk objects with text, token_count, page_number, chunk_index.
    """
    if not pages:
        return []
    
    full_text="\n\n---PAGE_BREAK---\n\n".join(p.text for p in pages)

    # Split on headings, keeping the heading lines
    # Result: ["text before first heading", "# Heading 1", "content under heading 1", "## Heading 2", ...]
    parts=_HEADING_RE.split(full_text)

    # Rebuild: each heading+ it's following content=a "section"
    sections:list[str]=[]
    current=""
    for part in parts:
        if _HEADING_RE.match(part):
            # This part is a heading- start a new section
            if current:
                sections.append(current.strip())
            current=part
        
        else:
            # content belongs to current heading
            current+="\n"+part
    if current:
        sections.append(current.strip())

    return _pack_sections_into_chunks(sections,token_counter,chunk_size,chunk_overlap)

def _pack_sections_into_chunks(
    sections: list[str],
    token_counter: Callable[[str],int],
    chunk_size:int,
    chunk_overlap:int,
) -> list[Chunk]:
    """
    Greedy pack sections into chunks of ~chunk_size tokens.
    Adds overlap by including last 'chunk_overlap' tockens from previos chunk.
    """
    chunks:list[Chunk]=[]
    current_chunk_text=""
    current_tokens=0
    chunk_index=0

    for section in sections:
        section_tokens=token_counter(section)

        #if section alone exceeds chunk_size, we must split it.
        if section_tokens>chunk_size:
            # Flush current chunk first
            if current_chunk_text:
                chunks.append(Chunk(
                    text=current_chunk_text.strip(),
                    token_count=current_tokens,
                    page_number=1,
                    chunk_index=chunk_index
                ))
                chunk_index+=1
                current_chunk_text=""
                current_tokens=0
            
            #Split the large section by paragraphs/sentences(simple fallback)
            sub_chunks=_split_large_section(section, token_counter, chunk_size,chunk_overlap)
            for sc in sub_chunks:
                chunks.append(Chunk(
                    text=sc,
                    token_count=token_counter(sc),
                    page_number=1,
                    chunk_index=chunk_index,
                ))
                chunk_index+=1
            continue
    if current_tokens+section_tokens>chunk_size and current_chunk_text:
        #Finalize current chunk
        chunks.append(Chunk(
            text=current_chunk_text.strip(),
            token_count=current_tokens,
            page_number=1,
            chunk_index=chunk_index
        ))
        chunk_index+=1
        
        overlap_text=_get_overlap_text(current_chunk_text,token_counter,chunk_overlap)
        current_chunk_text=overlap_text+"\n\n"+section
        current_tokens=token_counter(current_chunk_text)
    else:
        #Add section to current chunk
        if current_chunk_text:
            current_chunk_text+="\n\n"+section
        else:
            current_chunk_text=section
        current_tokens= token_counter(current_chunk_text)
    
    #Don't forget last chunk
    #Flush the final chunk
    if current_chunk_text:
        chunks.append(Chunk(
            text=current_chunk_text.strip(),
            token_count=current_tokens,
            page_number=1,
            chunk_index=chunk_index
        ))
    
    return chunks

def _get_overlap_text(text:str,token_counter:Callable[[str],int],overlap_tokens:int)->str:
    """
    Return the last 'overlap_tokens' tokens from text as a string.
    simple approximation: slplit by whitespace, take last N words, rejoin.
    Good enough for overlap; exact token alignment not critical
    """
    if overlap_tokens<=0:
        return ""
    words=text.split()
    # Rough: 1 token ~ 0.75 words for english.
    approx_words=int(overlap_tokens*1.3)
    if len(words)<=approx_words:
        return text
    return " ".join(words[-approx_words:])

def _split_large_section(
    text: str,
    token_counter: Callable[[str], int],
    chunk_size: int,
    chunk_overlap: int,
) -> List[str]:
    """
    Fallback: split a too-large section by sentences.
    Returns list of text strings, each <= chunk_size tokens.
    """
    # Split by sentences (handles . ! ? followed by space)
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if not sentences:
        return [text]

    chunks = []
    current = ""
    current_tokens = 0

    for sent in sentences:
        sent_tokens = token_counter(sent)
        
        # If adding this sentence exceeds chunk size, finalize current chunk
        if current_tokens + sent_tokens > chunk_size and current:
            chunks.append(current.strip())
            # Start new chunk with overlap
            overlap = _get_overlap_text(current, token_counter, chunk_overlap)
            current = overlap + " " + sent
            current_tokens = token_counter(current)
        else:
            # Add sentence to current chunk
            if current:
                current += " " + sent
            else:
                current = sent
            current_tokens = token_counter(current)

    # Don't forget the last chunk
    if current:
        chunks.append(current.strip())
    
    return chunks


def chunk_pdf(
    pages: List[ParsedPage],
    token_counter: Callable[[str], int],
    chunk_size: int,
    chunk_overlap: int,
) -> List[Chunk]:
    """
    Chunk PDF pages — each page is already a logical unit.
    Pack pages into chunks; split large pages if needed.
    """
    chunks: List[Chunk] = []
    chunk_index = 0

    for page in pages:
        page_text = page.text.strip()
        if not page_text:
            continue

        page_tokens = token_counter(page_text)

        if page_tokens <= chunk_size:
            # Page fits in one chunk
            chunks.append(Chunk(
                text=page_text,
                token_count=page_tokens,
                page_number=page.page_number,
                chunk_index=chunk_index,
            ))
            chunk_index += 1
        else:
            # Page too large — split it
            sub_texts = _split_large_section(page_text, token_counter, chunk_size, chunk_overlap)
            for st in sub_texts:
                chunks.append(Chunk(
                    text=st,
                    token_count=token_counter(st),
                    page_number=page.page_number,
                    chunk_index=chunk_index,
                ))
                chunk_index += 1

    return chunks
    
def chunk_txt(
    pages: List[ParsedPage],
    token_counter: Callable[[str], int],
    chunk_size: int,
    chunk_overlap: int,
) -> List[Chunk]:
    """
    Chunk plain text — no structure, just sliding window with overlap.
    """
    if not pages:
        return []
    # TXT has one "page"
    full_text = pages[0].text.strip()
    if not full_text:
        return []

    # Split into words for sliding window
    words = full_text.split()
    if not words:
        return []

    chunks: List[Chunk] = []
    chunk_index = 0
    start = 0

    # Rough token-to-word ratio
    words_per_chunk = int(chunk_size * 1.3)
    overlap_words = int(chunk_overlap * 1.3)

    while start < len(words):
        end = min(start + words_per_chunk, len(words))
        chunk_words = words[start:end]
        chunk_text = " ".join(chunk_words)

        chunks.append(Chunk(
            text=chunk_text,
            token_count=token_counter(chunk_text),
            page_number=1,
            chunk_index=chunk_index,
        ))
        chunk_index += 1

        if end >= len(words):
            break
        # Move start forward by (chunk_size - overlap)
        start += words_per_chunk - overlap_words

    return chunks
            
def chunk_file(
    pages:List[ParsedPage],
    token_counter:Callable[[str],int],
    chunk_size:int,
    chunk_overlap:int,
    file_type:str,
) -> List[Chunk]:
    """
    Dispatch to the right chunker based on teh file type.

    Args:
        pages: Parsed pages from the document.
        token_counter: Function that returns token count for a string.
        chunk_size: Target tokens per chunk (from settings).
        chunk_overlap: Tokens to overlap between chunks (from settings).
        file_type: File type (txt,pdf,md)

    Returns:
        List of Chunk objects with text, token_count, page_number, chunk_index.
    """
    if file_type == "pdf":
        return chunk_pdf(pages, token_counter, chunk_size, chunk_overlap)
    elif file_type in ("txt",):
        return chunk_txt(pages, token_counter, chunk_size, chunk_overlap)
    elif file_type in ("md", "markdown"):
        return chunk_markdown(pages, token_counter, chunk_size, chunk_overlap)
    else:
        raise ValueError(f"Unknown file type for chunking: {file_type}")
    
