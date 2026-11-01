import numpy as np
import pytest

from app.rag.ingestion.chunker import Chunk
from app.rag.ingestion.embedder import(
    embed_documents,
    embed_queries,
    embed_chunks,
    fake_embed_documents,
    fake_embed_queries,
    fake_embed_chunks,
)

#Fake Embedder tests

def test_fake_embed_documents_returns_correct_shape():
    texts = ["Hello world", "Another text"]
    embeddings = fake_embed_documents(texts)

    assert len(embeddings) == 2
    assert all(e.shape==(768,) for e in embeddings)
    assert all(e.dtype==np.float32 for e in embeddings)

def test_fake_embed_queries_returns_correct_shape():
    texts=["test query"]
    embeddings=fake_embed_queries(texts)

    assert len(embeddings)==1
    assert embeddings[0].shape==(768,)
    assert embeddings[0].dtype==np.float32

def test_fake_embed_deterministic():
    "same input + same prefix = same output."
    e1=fake_embed_documents(["test"])
    e2=fake_embed_documents(["test"])
    assert np.allclose(e1[0],e2[0])

def test_fake_embed_different_inputs_different_outputs():
    e = fake_embed_documents(["text one", "text two"])
    assert not np.allclose(e[0], e[1])


def test_fake_embed_chunks_attaches_embeddings():
    chunks = [
        Chunk(text="First chunk", token_count=10, page_number=1, chunk_index=0),
        Chunk(text="Second chunk", token_count=12, page_number=1, chunk_index=1),
    ]

    result = fake_embed_chunks(chunks)

    assert len(result) == 2
    for chunk in result:
        assert chunk.embedding is not None
        assert len(chunk.embedding) == 768
        assert chunk.embedding_model == "fake-nomic-embed-text"


def test_fake_embed_chunks_empty_list():
    assert fake_embed_chunks([]) == []
    assert fake_embed_documents([]) == []
    assert fake_embed_queries([]) == []


def test_fake_prefixes_are_different():
    """Verify search_document: and search_query: produce different vectors for same text."""
    doc_emb = fake_embed_documents(["identical text"])
    query_emb = fake_embed_queries(["identical text"])
    assert not np.allclose(doc_emb[0], query_emb[0])


# ---- Real Ollama embedder tests (require Ollama running) ----

@pytest.mark.integration
def test_ollama_embed_documents_dimension():
    """Integration test: real Ollama call returns 768-dim vectors."""
    embeddings = embed_documents(["hello world"])
    assert len(embeddings) == 1
    assert len(embeddings[0]) == 768
    assert embeddings[0].dtype == np.float32


@pytest.mark.integration
def test_ollama_embed_queries_dimension():
    embeddings = embed_queries(["test query"])
    assert len(embeddings) == 1
    assert len(embeddings[0]) == 768


@pytest.mark.integration
def test_ollama_prefixes_produce_different_vectors():
    """Integration test: prefixes create different vectors for same text."""
    doc_emb = embed_documents(["same text"])
    query_emb = embed_queries(["same text"])
    assert not np.allclose(doc_emb[0], query_emb[0])


@pytest.mark.integration
def test_ollama_embed_chunks():
    chunks = [
        Chunk(text="Test chunk", token_count=5, page_number=1, chunk_index=0),
    ]
    result = embed_chunks(chunks)
    assert len(result) == 1
    assert len(result[0].embedding) == 768
    assert result[0].embedding_model == "nomic-embed-text"  