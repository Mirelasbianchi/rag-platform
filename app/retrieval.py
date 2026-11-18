"""Retrieval strategies: vector, keyword and hybrid (reciprocal rank fusion)."""

from enum import StrEnum

from app import db, rag

RRF_K = 60  # standard constant from Cormack et al. (2009)


class Mode(StrEnum):
    vector = "vector"
    keyword = "keyword"
    hybrid = "hybrid"


def reciprocal_rank_fusion(rankings: list[list[dict]], k: int) -> list[dict]:
    """Fuse ranked lists: score(d) = sum over lists of 1 / (RRF_K + rank)."""
    scores: dict[int, float] = {}
    hits: dict[int, dict] = {}
    for ranking in rankings:
        for rank, hit in enumerate(ranking, start=1):
            scores[hit["chunk_id"]] = scores.get(hit["chunk_id"], 0.0) + 1 / (RRF_K + rank)
            hits.setdefault(hit["chunk_id"], hit)
    best = sorted(scores, key=scores.get, reverse=True)[:k]
    return [{**hits[chunk_id], "score": round(scores[chunk_id], 6)} for chunk_id in best]


def retrieve(query: str, k: int, mode: Mode = Mode.hybrid) -> list[dict]:
    if mode == Mode.keyword:
        return db.keyword_search(query, k)
    [query_vector] = rag.embed([query])
    if mode == Mode.vector:
        return db.vector_search(query_vector, k)
    pool = max(4 * k, 20)  # retrieve deeper lists so fusion has candidates to promote
    return reciprocal_rank_fusion(
        [db.vector_search(query_vector, pool), db.keyword_search(query, pool)], k
    )
