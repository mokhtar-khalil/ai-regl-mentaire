"""FastAPI backend for the regulatory RAG. Sourced Q&A over the indexed corpus."""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv(".env")

from fastapi import FastAPI
from pydantic import BaseModel

from app.documents import label_for
from app.embeddings import embed_query
from app.generate import answer
from app.index_store import hybrid_search

app = FastAPI(title="RAG Réglementaire API")


class AskRequest(BaseModel):
    question: str
    top_k: int = 10


class Source(BaseModel):
    index: int
    document: str
    document_label: str
    chapter: str | None = None
    article_num: str | None = None
    article_title: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    rrf_score: float | None = None


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    query_vector = embed_query(req.question)
    chunks = hybrid_search(req.question, query_vector, top_k=req.top_k)
    response_text = answer(req.question, chunks)
    sources = [
        Source(
            index=i,
            document=c.get("document"),
            document_label=label_for(c.get("document")),
            chapter=c.get("chapter"),
            article_num=c.get("article_num"),
            article_title=c.get("article_title"),
            page_start=c.get("page_start"),
            page_end=c.get("page_end"),
            rrf_score=c.get("rrf_score"),
        )
        for i, c in enumerate(chunks, start=1)
    ]
    return AskResponse(answer=response_text, sources=sources)
