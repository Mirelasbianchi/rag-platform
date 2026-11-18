"""Chunking and embeddings."""

import re

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


_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*$", re.MULTILINE)


def split_sections(text: str) -> list[tuple[str, str]]:
    """Split Markdown into (heading path, body) sections. Plain text is one section."""
    sections, path = [], []
    matches = list(_HEADING.finditer(text))
    if not matches or matches[0].start() > 0:
        preamble = text[: matches[0].start()] if matches else text
        if preamble.strip():
            sections.append(("", preamble))
    for i, match in enumerate(matches):
        level, title = len(match.group(1)), match.group(2).strip()
        path = [*path[: level - 1], title]
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[match.end() : end]
        if body.strip():
            sections.append((" > ".join(path), body))
    return sections


def chunk_markdown(text: str, size: int, overlap: int) -> list[str]:
    """Chunk each section separately and prefix chunks with their heading path.

    Keeping chunks inside one section avoids mixing unrelated topics, and the heading
    prefix gives both the embedding and the keyword index the section's context.
    """
    chunks = []
    for heading, body in split_sections(text):
        prefix = f"{heading}\n" if heading else ""
        budget = max(size - len(prefix), overlap + 50)
        chunks += [prefix + chunk for chunk in chunk_text(body, budget, overlap)]
    return chunks


def embed(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    return embeddings.embed(texts, settings.embedding_model, settings.embedding_dim)
