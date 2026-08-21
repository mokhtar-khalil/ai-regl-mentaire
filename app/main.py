"""FastAPI backend for the regulatory RAG. Sourced Q&A over the indexed corpus."""

from __future__ import annotations

import re

from dotenv import load_dotenv

load_dotenv(".env")

from fastapi import FastAPI
from pydantic import BaseModel

from app.documents import label_for
from app.embeddings import embed_query
from app.generate import answer
from app.index_store import hybrid_search

app = FastAPI(title="RégleMarchés AI API")


class AskRequest(BaseModel):
    question: str
    top_k: int = 10
    target_lang: str | None = None  # "fr" | "ar" | None (match the question's language)


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


_CITATION_RE = re.compile(r"\[(\d+)\]")


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    query_vector = embed_query(req.question)
    chunks = hybrid_search(req.question, query_vector, top_k=req.top_k)
    response_text = answer(req.question, chunks, target_lang=req.target_lang)

    # top_k retrieves a broad candidate pool so the model has enough to work
    # with (see hybrid_search's docstring) — most of those chunks never end
    # up cited. Showing all of them as "sources" makes the reader wonder why
    # a source is listed that the answer never mentions. Keep only the ones
    # the model actually cited, in the order it cited them.
    cited_indices = [int(n) for n in dict.fromkeys(_CITATION_RE.findall(response_text))]

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
        if i in cited_indices
    ]
    return AskResponse(answer=response_text, sources=sources)
