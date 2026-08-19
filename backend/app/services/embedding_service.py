"""
KnowledgeHub — Embedding Service
=================================
Generates deterministic dense vector embeddings for text chunks using
BAAI/bge-small-en-v1.5 via fastembed (local ONNX Runtime).

Design principles:
- Lazy model loading: Model weights are loaded/cached on first invocation,
  preventing mandatory download/blocking during normal application startup.
- Configurable model & dimension (default: BAAI/bge-small-en-v1.5 with 384 dimensions).
- Strict dimension validation on all generated embeddings.
- Batched inference for high-throughput CPU processing.
"""

from typing import Iterable
import numpy as np
from app.config import settings

# Module-level cached model instance
_model_instance = None


class EmbeddingServiceError(Exception):
    """Exception raised when embedding generation or model loading fails."""
    pass


def get_model():
    """
    Lazy-load and cache the fastembed TextEmbedding model.
    Only called when embedding generation is explicitly requested.
    """
    global _model_instance
    if _model_instance is None:
        try:
            from fastembed import TextEmbedding
            _model_instance = TextEmbedding(model_name=settings.embedding_model)
        except Exception as exc:
            raise EmbeddingServiceError(
                f"Failed to initialize embedding model '{settings.embedding_model}': {exc}"
            ) from exc
    return _model_instance


def embed_text(text: str) -> list[float]:
    """
    Generate a normalized dense vector embedding for a single string.

    Args:
        text: Input string.

    Returns:
        List of floats with length equal to settings.embedding_dimensions (384).

    Raises:
        EmbeddingServiceError: On model failure or dimension mismatch.
    """
    clean_text = text.strip()
    if not clean_text:
        # Return a zero vector for empty/whitespace input
        return [0.0] * settings.embedding_dimensions

    embeddings = embed_batch([clean_text])
    return embeddings[0]


def embed_batch(
    texts: list[str],
    batch_size: int | None = None,
) -> list[list[float]]:
    """
    Generate normalized dense vector embeddings for a list of strings in batches.

    Args:
        texts: List of input strings.
        batch_size: Optional batch size override (defaults to settings.embedding_batch_size).

    Returns:
        List of float vectors, each of length settings.embedding_dimensions.

    Raises:
        EmbeddingServiceError: On model failure or dimension mismatch.
    """
    if not texts:
        return []

    model = get_model()
    actual_batch_size = batch_size or settings.embedding_batch_size

    # Handle empty/whitespace strings by replacing with a space to avoid model crashes,
    # then zeroing out the resulting vectors if appropriate
    sanitized_texts = [t if t.strip() else " " for t in texts]

    try:
        raw_embeddings: Iterable[np.ndarray] = model.embed(
            sanitized_texts,
            batch_size=actual_batch_size,
        )
        result: list[list[float]] = []

        for idx, vec in enumerate(raw_embeddings):
            if not texts[idx].strip():
                # For originally empty strings, produce an explicit zero vector
                vector_list = [0.0] * settings.embedding_dimensions
            else:
                vector_list = vec.tolist()

            if len(vector_list) != settings.embedding_dimensions:
                raise EmbeddingServiceError(
                    f"Embedding dimension mismatch: expected {settings.embedding_dimensions}, "
                    f"got {len(vector_list)} for model '{settings.embedding_model}'."
                )

            result.append(vector_list)

        return result

    except EmbeddingServiceError:
        raise
    except Exception as exc:
        raise EmbeddingServiceError(
            f"Failed generating embeddings with model '{settings.embedding_model}': {exc}"
        ) from exc


def get_embedding_model_info() -> dict[str, str | int]:
    """Return metadata about the active embedding configuration."""
    return {
        "model": settings.embedding_model,
        "dimensions": settings.embedding_dimensions,
        "batch_size": settings.embedding_batch_size,
    }
