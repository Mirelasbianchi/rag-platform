from fastapi import FastAPI
from pydantic import BaseModel, Field

from app import db, rag
from app.config import get_settings
from app.retrieval import Mode, retrieve

app = FastAPI(title="RAG Platform", version="0.1.0")


class DocumentIn(BaseModel):
    title: str
    text: str = Field(min_length=1)
    source: str | None = None


class DocumentOut(BaseModel):
    document_id: int
    chunks: int


class SearchIn(BaseModel):
    query: str = Field(min_length=1)
    k: int = Field(default=5, ge=1, le=50)
    mode: Mode = Mode.hybrid


class SearchHit(BaseModel):
    chunk_id: int
    document_id: int
    title: str
    source: str | None = None
    content: str
    score: float


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/documents", response_model=DocumentOut, status_code=201)
def ingest(doc: DocumentIn) -> DocumentOut:
    settings = get_settings()
    chunks = rag.chunk_text(doc.text, settings.chunk_size, settings.chunk_overlap)
    vectors = rag.embed(chunks)
    doc_id = db.insert_document(doc.title, doc.source, chunks, vectors)
    return DocumentOut(document_id=doc_id, chunks=len(chunks))


@app.post("/search", response_model=list[SearchHit])
def search(body: SearchIn) -> list[SearchHit]:
    return [SearchHit(**hit) for hit in retrieve(body.query, body.k, body.mode)]
