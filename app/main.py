"""FastAPI backend for the regulatory RAG. Sourced Q&A over the indexed corpus."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import Literal

from dotenv import load_dotenv

load_dotenv(".env")

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.documents import label_for
from app.embeddings import embed_query
from app.generate import answer, answer_stream
from app.index_store import hybrid_search, ping_qdrant
from app.query_translate import detect_lang, translate_query

logger = logging.getLogger("uvicorn.error")
logger.setLevel(logging.INFO)


def _log_event(event: str, **details) -> None:
    logger.info(json.dumps({"event": event, **details}, ensure_ascii=False))


def _keepalive_interval() -> float:
    try:
        return max(0.0, float(os.getenv("QDRANT_KEEPALIVE_SECONDS", "240")))
    except ValueError:
        return 240.0


async def _qdrant_keepalive_loop(interval: float) -> None:
    _log_event("qdrant_keepalive_started", interval_seconds=interval)
    while True:
        await asyncio.sleep(interval)
        started = time.perf_counter()
        try:
            await asyncio.to_thread(ping_qdrant)
            _log_event(
                "qdrant_keepalive",
                status="ok",
                duration_ms=round((time.perf_counter() - started) * 1000, 1),
            )
        except Exception as exc:
            logger.warning(
                json.dumps(
                    {
                        "event": "qdrant_keepalive",
                        "status": "error",
                        "error": str(exc),
                        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                    },
                    ensure_ascii=False,
                )
            )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    interval = _keepalive_interval()
    keepalive_task = None
    if os.environ.get("QDRANT_URL") and interval > 0:
        keepalive_task = asyncio.create_task(_qdrant_keepalive_loop(interval))
    try:
        yield
    finally:
        if keepalive_task:
            keepalive_task.cancel()
            try:
                await keepalive_task
            except asyncio.CancelledError:
                pass


app = FastAPI(title="RégleMarchés AI API", lifespan=lifespan)


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


def _source_models(chunks: list[dict], cited_indices: list[int]) -> list[Source]:
    return [
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


def _timed_call(function, *args):
    started = time.perf_counter()
    result = function(*args)
    return result, round((time.perf_counter() - started) * 1000, 1)


def _prepare_chunks(req: AskRequest) -> tuple[list[dict], dict[str, float]]:
    """Run the two independent Gemini preparations concurrently."""
    preparation_started = time.perf_counter()
    other_lang = "fr" if detect_lang(req.question) == "ar" else "ar"

    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="rag-prepare") as executor:
        embedding_future = executor.submit(_timed_call, embed_query, req.question)
        translation_future = executor.submit(
            _timed_call,
            translate_query,
            req.question,
            other_lang,
        )
        query_vector, embedding_ms = embedding_future.result()
        translated_query, translation_ms = translation_future.result()

    parallel_preparation_ms = round(
        (time.perf_counter() - preparation_started) * 1000,
        1,
    )
    search_started = time.perf_counter()
    chunks = hybrid_search(
        req.question,
        query_vector,
        top_k=req.top_k,
        translated_query=translated_query,
    )
    search_ms = round((time.perf_counter() - search_started) * 1000, 1)
    return chunks, {
        "embedding_ms": embedding_ms,
        "translation_ms": translation_ms,
        "parallel_preparation_ms": parallel_preparation_ms,
        "search_ms": search_ms,
    }


def _ndjson(event: dict) -> bytes:
    return (json.dumps(event, ensure_ascii=False) + "\n").encode("utf-8")


class _StreamingCitationMapper:
    def __init__(self, chunks: list[dict]):
        self.chunks = chunks
        self.visible_by_source: dict[tuple, int] = {}
        self.mapping: dict[int, int] = {}

    def normalize(self, text: str) -> str:
        for raw in _CITATION_RE.findall(text):
            original_index = int(raw)
            if not 1 <= original_index <= len(self.chunks):
                continue
            if original_index not in self.mapping:
                identity = _source_identity(self.chunks[original_index - 1])
                visible_index = self.visible_by_source.get(identity)
                if visible_index is None:
                    visible_index = len(self.visible_by_source) + 1
                    self.visible_by_source[identity] = visible_index
                self.mapping[original_index] = visible_index

        def replace(match: re.Match) -> str:
            original_index = int(match.group(1))
            return (
                f"[{self.mapping[original_index]}]"
                if original_index in self.mapping
                else ""
            )

        normalized = _CITATION_RE.sub(replace, text)
        return re.sub(r"(\[\d+\])(?:\1)+", r"\1", normalized)


def _stream_ask(req: AskRequest, request_id: str):
    total_started = time.perf_counter()
    yield _ndjson({"type": "status", "request_id": request_id, "stage": "preparing"})

    try:
        chunks, timings = _prepare_chunks(req)
        generation_started = time.perf_counter()
        first_answer_ms = None
        mapper = _StreamingCitationMapper(chunks)

        for event_type, payload in answer_stream(
            req.question,
            chunks,
            target_lang=req.target_lang,
        ):
            if event_type == "delta":
                if first_answer_ms is None:
                    first_answer_ms = round((time.perf_counter() - total_started) * 1000, 1)
                yield _ndjson({"type": "delta", "text": mapper.normalize(payload)})
                continue

            response_text, cited_indices = _renumber_citations(payload, chunks)
            sources = _source_models(chunks, cited_indices)
            timings.update(
                {
                    "generation_ms": round((time.perf_counter() - generation_started) * 1000, 1),
                    "time_to_first_answer_ms": first_answer_ms,
                    "total_ms": round((time.perf_counter() - total_started) * 1000, 1),
                }
            )
            _log_event(
                "ask_completed",
                request_id=request_id,
                streaming=True,
                chunks=len(chunks),
                sources=len(sources),
                **timings,
            )
            yield _ndjson(
                {
                    "type": "done",
                    "answer": response_text,
                    "sources": [source.model_dump() for source in sources],
                    "timings": timings,
                }
            )
    except Exception as exc:
        logger.exception(
            json.dumps(
                {
                    "event": "ask_failed",
                    "request_id": request_id,
                    "streaming": True,
                    "total_ms": round((time.perf_counter() - total_started) * 1000, 1),
                    "error": str(exc),
                },
                ensure_ascii=False,
            )
        )
        yield _ndjson({"type": "error", "error": "La génération de la réponse a échoué."})


@app.post("/ask/stream")
def ask_streaming(req: AskRequest):
    request_id = uuid.uuid4().hex[:12]
    return StreamingResponse(
        _stream_ask(req, request_id),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    request_id = uuid.uuid4().hex[:12]
    total_started = time.perf_counter()
    chunks, timings = _prepare_chunks(req)
    generation_started = time.perf_counter()
    response_text = answer(req.question, chunks, target_lang=req.target_lang)
    response_text, cited_indices = _renumber_citations(response_text, chunks)
    sources = _source_models(chunks, cited_indices)
    timings.update(
        {
            "generation_ms": round((time.perf_counter() - generation_started) * 1000, 1),
            "total_ms": round((time.perf_counter() - total_started) * 1000, 1),
        }
    )
    _log_event(
        "ask_completed",
        request_id=request_id,
        streaming=False,
        chunks=len(chunks),
        sources=len(sources),
        **timings,
    )
    return AskResponse(answer=response_text, sources=sources)
