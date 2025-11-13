"""Embedding service for knowledge base vectorization.

Supports OpenAI-compatible embedding APIs (OpenAI, Azure, LocalAI, etc.).
Reads from environment: EMBEDDING_API_KEY, EMBEDDING_BASE_URL, EMBEDDING_MODEL.
"""

from __future__ import annotations

import os
from typing import List, Optional

from openai import OpenAI


_client: Optional[OpenAI] = None
_model: str = "text-embedding-3-small"  # default


def init_embedding_client() -> None:
    """Initialize embedding client from environment variables."""
    global _client, _model
    api_key = os.environ.get("EMBEDDING_API_KEY") or os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("EMBEDDING_BASE_URL")
    model = os.environ.get("EMBEDDING_MODEL")
    if model:
        _model = model
    if api_key:
        _client = OpenAI(api_key=api_key, base_url=base_url)


def is_enabled() -> bool:
    return _client is not None


def embed_text(text: str) -> List[float]:
    """Generate embedding vector for a single text string."""
    if not is_enabled():
        raise RuntimeError("Embedding client not initialized (missing EMBEDDING_API_KEY or OPENAI_API_KEY)")
    assert _client is not None
    response = _client.embeddings.create(input=[text], model=_model)
    return response.data[0].embedding


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Batch generate embeddings for multiple text strings."""
    if not is_enabled():
        raise RuntimeError("Embedding client not initialized")
    assert _client is not None
    if not texts:
        return []
    response = _client.embeddings.create(input=texts, model=_model)
    return [item.embedding for item in response.data]


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    import math
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


__all__ = [
    "init_embedding_client",
    "is_enabled",
    "embed_text",
    "embed_texts",
    "cosine_similarity",
]
