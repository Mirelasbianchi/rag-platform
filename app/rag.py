"""Chunking and embeddings."""

from app import embeddings
from app.config import get_settings


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    """Split text into chunks of about `size` characters, breaking on whitespace."""
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")
    words = text.split()
    chunks, current = [], []
    length = 0
    for word in words:
        if length + len(word) + 1 > size and current:
            chunks.append(" ".join(current))
            # keep the tail of the previous chunk as overlap
            tail, tail_len = [], 0
            for w in reversed(current):
                if tail_len + len(w) + 1 > overlap:
                    break
                tail.insert(0, w)
                tail_len += len(w) + 1
            current, length = tail, tail_len
        current.append(word)
        length += len(word) + 1
    if current:
        chunks.append(" ".join(current))
    return chunks


def embed(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    return embeddings.embed(texts, settings.embedding_model, settings.embedding_dim)
