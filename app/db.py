"""PostgreSQL + pgvector access."""

from functools import lru_cache

import numpy as np
from pgvector.psycopg import register_vector
from psycopg_pool import ConnectionPool

from app.config import get_settings


@lru_cache
def get_pool() -> ConnectionPool:
    return ConnectionPool(
        get_settings().database_url,
        configure=register_vector,
        open=True,
    )


def insert_document(title: str, source: str | None, chunks: list[str], vectors) -> int:
    with get_pool().connection() as conn:
        doc_id = conn.execute(
            "INSERT INTO documents (title, source) VALUES (%s, %s) RETURNING id",
            (title, source),
        ).fetchone()[0]
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO chunks (document_id, position, content, embedding) "
                "VALUES (%s, %s, %s, %s)",
                [
                    (doc_id, i, chunk, np.array(vec))
                    for i, (chunk, vec) in enumerate(zip(chunks, vectors, strict=True))
                ],
            )
    return doc_id


def search(query_vector, k: int) -> list[dict]:
    with get_pool().connection() as conn:
        rows = conn.execute(
            """
            SELECT c.id, c.document_id, d.title, c.content,
                   1 - (c.embedding <=> %s) AS score
            FROM chunks c JOIN documents d ON d.id = c.document_id
            ORDER BY c.embedding <=> %s
            LIMIT %s
            """,
            (np.array(query_vector), np.array(query_vector), k),
        ).fetchall()
    keys = ["chunk_id", "document_id", "title", "content", "score"]
    return [dict(zip(keys, row, strict=True)) for row in rows]
