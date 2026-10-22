"Embeddings generation using sentence-transformers"

# from app.db.models import Chunk
# from app.core.config import Settings
from app.db.models import Chunk
from functools import lru_cache
from typing import List

import numpy as np 
from sentence_transformers import SentenceTransformer

from app.core.config import get_settings
from app.rag.ingestion.chunker import Chunk as ChunkDataclass


#Global model cache- loaded once, reused across calls
@lru_cache(maxsize=1)
def get_embedding_model()->SentenceTransformer:
    """
    Load the embedding model (cached).

    Uses settings.embedding_model (defualt: BAAI/bge-small-en-v1.5).
    Downloads on first use (~90MB), then caches locally.
    """
    settings= get_settings()
    model=SentenceTransformer(settings.embedding_model)
    #Ensure model outputs correct dimension
    assert model.get_sentence_embedding_dimension()==settings.embedding_dim
    return model

def embed_texts(texts: List[str])-> List[np.ndarray]:
    """
    Generate embeddings for a list of texts.

    Args:
        texts List of strings to embed.

    Returns:
        List of numpy arrays (float32), each of shape (embedding_dim,)
    """
    if not texts:
        return []
    
    model=get_embedding_model()
    # encode() returns numpy array of shape (len(texts),embedding_dim)
    embeddings=model.encode(
        texts,
        batch_size=32,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    #return as list of !d arrays
    return [emb.astype(np.float32) for emb in embeddings]

def embed_chunks(chunks: List["ChunkDataclass"])-> List["ChunkDataclass"]:
    """
    Add embeddings to Chunk objects in place.

    Args:
        chunks List of Chunk objects (from chunker).

    Returns:
        Same list, with each chunk's embedding computed.
    """
    if not chunks:
        return chunks
    
    texts = [c.text for c in chunks]
    embeddings = embed_texts(texts)
    model_name=get_settings().embedding_model
    
     # Create NEW chunks with embeddings (can't modify frozen dataclass)
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

#Line-by-line explanation
#@lru_cache(maxsize=1) : Caches the model — first call loads it (~90MB download), subsequent calls return cached instance
# get_embedding_model() : Returns SentenceTransformer loaded with model from settings
# assert model.get_sentence_embedding_dimension() == settings.embedding_dim : Safety check: model dimension matches config (384)
# embed_texts(texts) : Batch encodes all texts. normalize_embeddings=True = vectors unit length (cosine = dot product)
# emb.astype(np.float32) : Ensure float32 (smaller, matches pgvector)
# embed_chunks(chunks) : Convenience: takes Chunk objects, adds embedding (list[float]) and embedding_model (str)

# Key Python features for beginners
# 1. @lru_cache — Memoization decorator. Function runs once per unique args; subsequent calls return cached result. Here maxsize=1 = only cache the latest (only one model anyway).
# 2. SentenceTransformer.encode() — Batch processes texts efficiently on CPU/GPU. Returns numpy.ndarray.
# 3. np.ndarray.tolist() — Converts numpy array to Python list (required for SQLAlchemy/pgvector).
# 4. Forward reference "Chunk" — In type hints, List["Chunk"] (quotes) allows referencing a class defined later or in another module.
# 5. zip(chunks, embeddings) — Pairs corresponding elements from two lists.

