from app import retrieval


def hit(chunk_id: int) -> dict:
    return {"chunk_id": chunk_id, "document_id": chunk_id, "title": "t", "source": None,
            "content": "c", "score": 0.0}


def test_rrf_promotes_chunks_ranked_well_in_both_lists():
    vector = [hit(1), hit(2), hit(3)]
    keyword = [hit(3), hit(4), hit(1)]
    fused = retrieval.reciprocal_rank_fusion([vector, keyword], k=3)
    assert [h["chunk_id"] for h in fused][:2] == [1, 3]


def test_rrf_respects_k():
    assert len(retrieval.reciprocal_rank_fusion([[hit(i) for i in range(10)]], k=4)) == 4


def test_keyword_mode_skips_embeddings(monkeypatch):
    def fail(_):
        raise AssertionError("embed should not be called")

    monkeypatch.setattr(retrieval.rag, "embed", fail)
    monkeypatch.setattr(retrieval.db, "keyword_search", lambda q, k: [hit(9)])
    assert retrieval.retrieve("prazo", 3, retrieval.Mode.keyword)[0]["chunk_id"] == 9
