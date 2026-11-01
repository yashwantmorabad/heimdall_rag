"Embeddings generation using ollama."

import httpx
import numpy as np 
from typing import List

from app.core.config import get_settings
from app.rag.ingestion.chunker import Chunk as ChunkDataclass

OLLAMA_EMBED_ENDPOINT="/api/embed"
DEFAULT_TIMEOUT=120.0

def _get_embed_url()-> str:
    "Build the ollama embed endpoint URL."
    settings=get_settings()
    base=settings.embedding_base_url or settings.llm_base_url
    return f"{base.rstrip('/')}{OLLAMA_EMBED_ENDPOINT}"

def _embed_batch(texts: List[str], prefix: str)-> List[np.ndarray]:
    "Embed a batch of texts with the given prefix via ollama."

    if not texts:
        return[]

    url=_get_embed_url()
    payload={
        "model": get_settings().embedding_model,
        "input":[f"{prefix}{t}" for t in texts],
    }

    try:
        with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
            resp=client.post(url,json=payload)
            resp.raise_for_status()
            data=resp.json()

    except httpx.ConnectError as e:
        raise RuntimeError(
            f"Cannot connect to ollama at {url}. Is ollama running?"
            f"Start it with: ollama serve"
        ) from e

    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"Ollama embed failed ({e.response.status_code}): {e.response.text}") from e

    embeddings=data.get("embeddings",[])
    if len(embeddings)!=len(texts):
        raise RuntimeError(f"Ollama returned {len(embeddings)} embeddings for {len(texts)} inputs")

    #convert to float32 numpy arrays
    return [np.array(e, dtype=np.float32) for e in embeddings]

def embed_documents(texts: List[str])-> List[np.ndarray]:
    "Embed document chunks with 'search_document:' prefix."
    return _embed_batch(texts, "search_document:")

def embed_queries(texts: List[str]) -> List[np.ndarray]:
    """Embed search queries with 'search_query: ' prefix."""
    return _embed_batch(texts, "search_query: ")


def embed_chunks(chunks: List[ChunkDataclass]) -> List[ChunkDataclass]:
    """Add embeddings to Chunk objects in place (for ingestion)."""
    if not chunks:
        return chunks

    texts = [c.text for c in chunks]
    embeddings = embed_documents(texts)
    model_name = get_settings().embedding_model

    result = []
    for chunk, emb in zip(chunks, embeddings):
        new_chunk = ChunkDataclass(
            text=chunk.text,
            token_count=chunk.token_count,
            page_number=chunk.page_number,
            chunk_index=chunk.chunk_index,
            embedding=emb.tolist(),
            embedding_model=model_name,
        )
        result.append(new_chunk)

    return result


# ---- Fake embedder for tests (no Ollama needed) ----

FAKE_DIM = 768  # matches nomic-embed-text


def _fake_embed(texts: List[str], prefix: str) -> List[np.ndarray]:
    """Deterministic fake embedder for tests."""
    embeddings = []
    for text in texts:
        # Hash the prefixed text for deterministic output
        hash_val = abs(hash(f"{prefix}{text}")) % (2**32)
        np.random.seed(hash_val)
        vec = np.random.randn(FAKE_DIM).astype(np.float32)
        vec = vec / np.linalg.norm(vec)  # normalize like real model
        embeddings.append(vec)
    return embeddings


def fake_embed_documents(texts: List[str]) -> List[np.ndarray]:
    return _fake_embed(texts, "search_document: ")


def fake_embed_queries(texts: List[str]) -> List[np.ndarray]:
    return _fake_embed(texts, "search_query: ")


def fake_embed_chunks(chunks: List[ChunkDataclass]) -> List[ChunkDataclass]:
    """Fake version of embed_chunks for testing."""
    if not chunks:
        return chunks

    texts = [c.text for c in chunks]
    embeddings = fake_embed_documents(texts)
    result = []
    for chunk, emb in zip(chunks, embeddings):
        new_chunk = ChunkDataclass(
            text=chunk.text,
            token_count=chunk.token_count,
            page_number=chunk.page_number,
            chunk_index=chunk.chunk_index,
            embedding=emb.tolist(),
            embedding_model="fake-nomic-embed-text",
        )
        result.append(new_chunk)
    return result