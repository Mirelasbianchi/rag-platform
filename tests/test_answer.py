from fastapi.testclient import TestClient

from app import answer, main

HITS = [
    {"chunk_id": 1, "document_id": 1, "title": "Art. 26", "source": "cdc", "score": 0.5,
     "content": "O direito de reclamar caduca em trinta dias para produtos não duráveis. "
                "Outro assunto qualquer."},
    {"chunk_id": 2, "document_id": 2, "title": "Art. 49", "source": "cdc", "score": 0.5,
     "content": "O consumidor pode desistir do contrato no prazo de 7 dias."},
]


def test_extractive_answer_cites_passages():
    text = answer.extractive_answer("Qual o prazo para desistir do contrato?", HITS)
    assert "[2]" in text
    assert "7 dias" in text


def test_extractive_answer_without_overlap():
    assert "could not find" in answer.extractive_answer("xyzzy", HITS)


def test_ask_endpoint_returns_citations(monkeypatch):
    monkeypatch.setattr(main, "retrieve", lambda q, k, mode: HITS)
    response = TestClient(main.app).post("/ask", json={"question": "prazo para desistir?"})
    body = response.json()
    assert response.status_code == 200
    assert body["strategy"] == "extractive"
    assert [c["n"] for c in body["citations"]] == [1, 2]
