import time

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app import answer as answering
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


class AskIn(BaseModel):
    question: str = Field(min_length=1)
    k: int = Field(default=4, ge=1, le=20)
    mode: Mode = Mode.hybrid


class Citation(BaseModel):
    n: int
    chunk_id: int
    document_id: int
    title: str
    source: str | None = None
    content: str


class AskOut(BaseModel):
    answer: str
    strategy: str
    citations: list[Citation]
    latency_ms: float


@app.post("/ask", response_model=AskOut)
def ask(body: AskIn) -> AskOut:
    start = time.perf_counter()
    hits = retrieve(body.question, body.k, body.mode)
    text, strategy = answering.answer(body.question, hits, get_settings().llm_model)
    citations = [
        Citation(n=i, **{key: hit[key] for key in Citation.model_fields if key != "n"})
        for i, hit in enumerate(hits, start=1)
    ]
    latency = round((time.perf_counter() - start) * 1000, 1)
    return AskOut(answer=text, strategy=strategy, citations=citations, latency_ms=latency)
