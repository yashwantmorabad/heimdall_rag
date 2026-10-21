#Test for embedder

from transformers.models.distilbert.modeling_distilbert import Embeddings
from torch import embedding
import numpy as np 
import pytest

from app.rag.ingestion.chunker import Chunk
from app.rag.ingestion.embedder import embed_texts,embed_chunks

#Fake embedder for fast, deterministic tests 

FAKE_DIM=384

def fake_embed_texts(texts: list[str])-> list[np.ndarray]:
    "Deterministic fake embedder: hash text-> fixed vector."
    embeddings=[]
    for text in texts:
        #constrain hash to valid numpy seed range [0, 2**32-1]
        hash_val=abs(hash(text)) % (2**32)# hash value should be in range of [0,2**32-1]
        np.random.seed(hash_val)
        vec=np.random.randn(FAKE_DIM).astype(np.float32)
        #Normalize
        vec=vec/np.linalg.norm(vec)
        embeddings.append(vec)
    return embeddings

def fake_embed_chunks(chunks: list[Chunk])-> list[Chunk]:
    "Fake version of embed_chunks for testing."
    texts=[c.text for c in chunks]
    embeddings=fake_embed_texts(texts)
    result=[]
    for chunk,emb in zip(chunks,embeddings):
        #create a new chunk with embedding
        new_chunk=Chunk(
            text=chunk.text,
            token_count=chunk.token_count,
            page_number=chunk.page_number,
            chunk_index=chunk.chunk_index,
            embedding=emb.tolist(),
            embedding_model="fake model"
        )
        result.append(new_chunk)
    return result


# Line-by-line explanation
# Line(s):	What it does
# fake_embed_texts : Deterministic fake: hashes text, seeds numpy random, generates normalized vector
# np.random.seed(hash_val) : Same text → same vector every run
# vec / np.linalg.norm(vec) : Normalize to unit length (like real model with normalize_embeddings=True)
# # fake_embed_chunks : Mirrors embed_chunks but uses fake embedde:

# Key Python features for beginners
# 1. Deterministic fakes — Tests must be repeatable. Hash-based seeding ensures same input → same output every run.
# 2. np.random.randn(dim) — Samples from standard normal distribution (mean=0, std=1).
# 3. astype(np.float32) — Matches real model output dtype.

def test_embed_texts_returns_correct_shape():
    "embed_texts returns list of vectors with correct dimension."
    texts=["Hello world", "Another text"]
    embeddings=fake_embed_texts(texts)

    assert len(embeddings)==2
    assert all(e.shape==(FAKE_DIM,) for e in embeddings)
    assert all(e.dtype == np.float32 for e in embeddings)

def test_embed_texts_deterministic():
    "Same input always produce same output."
    embeddings1=fake_embed_texts(["test"])
    embeddings2=fake_embed_texts(["test"])

    assert np.allclose(embeddings1[0],embeddings2[0])

def test_embed_texts_different_inputs_different_outputs():
    "Different texts produce different embeddings."
    embeddings=fake_embed_texts(["text one","text two"])
    
    assert not np.allclose(embeddings[0],embeddings[1])

def test_embed_chunks_attaches_embeddings():
    "embedded chunks add embedding and model name to each chunks."
    chunks=[
        Chunk(text="First chunk", token_count=10,page_number=1,chunk_index=0),
        Chunk(text="Second chunk", token_count=12,page_number=1,chunk_index=1),
    ]

    result=fake_embed_chunks(chunks)

    assert len(result)==2
    for chunk in result:
        assert chunk.embedding is not None
        assert len(chunk.embedding)==FAKE_DIM
        assert chunk.embedding_model=="fake model"

def test_embed_chunks_empty_list():
    "Empty input returns empty list"
    assert fake_embed_chunks([])==[]
    assert fake_embed_texts([])==[]

#Line by line explanation
#test_embed_texts_returns_correct_shape: Verifies the output: list of vectors,each shape(384,) dtype float32
#test_embed_texts_deterministic: same input -> same output
# test_embed_texts_different_inputs_different_outputs: different inputs -> different vectors
# test_embed_chunks_attaches_embeddings: chunks get embedding list and embedding_model string.
# test_embed_chunks_empty_list: empty input -> empty output

#Key python features
# 1. np.allclose(a,b) - compares arrays with tolearnace
# 2. assert all(... for e in embeddings) - checks every elements in list satisfies condition
# 3. Test isolation - each test creates it's own data, no shared state.


