"""PostgreSQL + pgvector access."""

from functools import lru_cache
from pathlib import Path

import numpy as np
from pgvector.psycopg import register_vector
from psycopg_pool import ConnectionPool

from app.config import get_settings

SCHEMA = Path(__file__).parent.parent / "db" / "init.sql"
HIT_KEYS = ["chunk_id", "document_id", "title", "source", "content", "score"]


def _configure(conn) -> None:
    # the extension must exist before the vector type can be registered
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    conn.commit()
    register_vector(conn)


@lru_cache
def get_pool() -> ConnectionPool:
    return ConnectionPool(get_settings().database_url, configure=_configure, open=True)


def init_schema() -> None:
    """Apply db/init.sql (idempotent). Used on startup when the database is managed, e.g. RDS."""
    with get_pool().connection() as conn:
        conn.execute(SCHEMA.read_text())


def ping() -> bool:
    with get_pool().connection() as conn:
        return conn.execute("SELECT 1").fetchone()[0] == 1


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


def list_documents() -> list[dict]:
    with get_pool().connection() as conn:
        rows = conn.execute(
            """
            SELECT d.id, d.title, d.source, d.created_at, count(c.id)
            FROM documents d LEFT JOIN chunks c ON c.document_id = d.id
            GROUP BY d.id ORDER BY d.id
            """
        ).fetchall()
    keys = ["document_id", "title", "source", "created_at", "chunks"]
    return [dict(zip(keys, row, strict=True)) for row in rows]


def delete_document(document_id: int) -> bool:
    with get_pool().connection() as conn:
        return conn.execute("DELETE FROM documents WHERE id = %s", (document_id,)).rowcount > 0


def vector_search(query_vector, k: int) -> list[dict]:
    """Nearest chunks by cosine similarity (HNSW index)."""
    with get_pool().connection() as conn:
        rows = conn.execute(
            """
            SELECT c.id, c.document_id, d.title, d.source, c.content,
                   1 - (c.embedding <=> %(q)s) AS score
            FROM chunks c JOIN documents d ON d.id = c.document_id
            ORDER BY c.embedding <=> %(q)s
            LIMIT %(k)s
            """,
            {"q": np.array(query_vector), "k": k},
        ).fetchall()
    return [dict(zip(HIT_KEYS, row, strict=True)) for row in rows]


def keyword_search(query: str, k: int) -> list[dict]:
    """Full-text search; terms are OR-ed so natural-language questions still match."""
    with get_pool().connection() as conn:
        rows = conn.execute(
            """
            WITH q AS (
                SELECT NULLIF(
                    replace(plainto_tsquery('portuguese', %(q)s)::text, '&', '|'), ''
                )::tsquery AS query
            )
            SELECT c.id, c.document_id, d.title, d.source, c.content,
                   ts_rank_cd(c.content_tsv, q.query) AS score
            FROM chunks c JOIN documents d ON d.id = c.document_id, q
            WHERE c.content_tsv @@ q.query
            ORDER BY score DESC
            LIMIT %(k)s
            """,
            {"q": query, "k": k},
        ).fetchall()
    return [dict(zip(HIT_KEYS, row, strict=True)) for row in rows]


def search(query_vector, k: int) -> list[dict]:
    """Backwards-compatible alias for vector search."""
    return vector_search(query_vector, k)
