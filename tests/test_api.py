from fastapi.testclient import TestClient

from app import main
from app.rag import chunk_text

client = TestClient(main.app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_chunk_text_respects_size():
    text = " ".join(["word"] * 500)
    chunks = chunk_text(text, size=100, overlap=20)
    assert len(chunks) > 1
    assert all(len(c) <= 100 for c in chunks)


def test_search_uses_embeddings_and_db(monkeypatch):
    from app import retrieval

    monkeypatch.setattr(retrieval.rag, "embed", lambda texts: [[0.1, 0.2]])
    monkeypatch.setattr(
        retrieval.db,
        "vector_search",
        lambda vec, k: [
            {"chunk_id": 1, "document_id": 7, "title": "Doc", "content": "x", "score": 0.9}
        ],
    )
    response = client.post("/search", json={"query": "hello", "k": 3, "mode": "vector"})
    assert response.status_code == 200
    assert response.json()[0]["document_id"] == 7


def test_hashing_embeddings_are_deterministic_and_normalized():
    import numpy as np

    from app.embeddings import hashing_embed

    a, b, c = hashing_embed(["Direito do consumidor", "direito do consumidor", "outro"], 256)
    assert a == b
    assert abs(np.linalg.norm(a) - 1) < 1e-5
    assert np.dot(a, b) > np.dot(a, c)


def test_chunk_markdown_keeps_heading_context():
    from app.rag import chunk_markdown

    text = "# Lei\n\n## Capítulo I\n\nTexto um.\n\n## Capítulo II\n\nTexto dois."
    chunks = chunk_markdown(text, size=200, overlap=20)
    assert chunks == ["Lei > Capítulo I\nTexto um.", "Lei > Capítulo II\nTexto dois."]


def test_upload_rejects_unsupported_files():
    response = client.post("/documents/upload", files={"file": ("a.exe", b"x")})
    assert response.status_code == 415
