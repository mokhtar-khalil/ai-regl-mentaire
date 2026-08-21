"""FastAPI backend for the regulatory RAG. Sourced Q&A over the indexed corpus."""

from __future__ import annotations

import re
from typing import Literal

from dotenv import load_dotenv

load_dotenv(".env")

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.documents import label_for
from app.embeddings import embed_query
from app.generate import answer
from app.index_store import hybrid_search

app = FastAPI(title="RégleMarchés AI API")


class AskRequest(BaseModel):
    question: str
    top_k: int = Field(default=7, ge=1, le=8)
    target_lang: Literal["fr", "ar"] | None = None


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


def _source_identity(chunk: dict) -> tuple:
    """Identify one user-visible legal provision across split text chunks."""
    article_num = chunk.get("article_num")
    if article_num:
        # Numbered paragraphs in development-bank documents restart inside
        # each chapter, unlike globally unique BCM article numbers.
        if "." in str(article_num):
            return chunk.get("document"), chunk.get("chapter"), str(article_num)
        return chunk.get("document"), str(article_num)
    return chunk.get("document"), chunk.get("page_start"), chunk.get("page_end")


def _renumber_citations(response_text: str, chunks: list[dict]) -> tuple[str, list[int]]:
    """Keep valid citations, merge duplicate provisions and number them contiguously."""
    raw_indices = [
        index
        for index in dict.fromkeys(int(n) for n in _CITATION_RE.findall(response_text))
        if 1 <= index <= len(chunks)
    ]
    cited_indices: list[int] = []
    visible_by_source: dict[tuple, int] = {}
    mapping: dict[int, int] = {}

    for original_index in raw_indices:
        identity = _source_identity(chunks[original_index - 1])
        visible_index = visible_by_source.get(identity)
        if visible_index is None:
            cited_indices.append(original_index)
            visible_index = len(cited_indices)
            visible_by_source[identity] = visible_index
        mapping[original_index] = visible_index

    def replace(match: re.Match) -> str:
        old = int(match.group(1))
        return f"[{mapping[old]}]" if old in mapping else ""

    normalized = _CITATION_RE.sub(replace, response_text)
    normalized = re.sub(r"(\[\d+\])(?:\1)+", r"\1", normalized)
    normalized = re.sub(r"\s+([.,;:!?])", r"\1", normalized)
    return normalized, cited_indices


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    query_vector = embed_query(req.question)
    chunks = hybrid_search(req.question, query_vector, top_k=req.top_k)
    response_text = answer(req.question, chunks, target_lang=req.target_lang)
    response_text, cited_indices = _renumber_citations(response_text, chunks)

    sources = [
        Source(
            index=visible_index,
            document=c.get("document"),
            document_label=label_for(c.get("document")),
            chapter=c.get("chapter"),
            article_num=c.get("article_num"),
            article_title=c.get("article_title"),
            page_start=c.get("page_start"),
            page_end=c.get("page_end"),
            rrf_score=c.get("rrf_score"),
        )
        for visible_index, original_index in enumerate(cited_indices, start=1)
        for c in [chunks[original_index - 1]]
    ]
    return AskResponse(answer=response_text, sources=sources)
