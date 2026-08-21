"""Hybrid index: Qdrant for semantic search, BM25 (in-process) for lexical.

Qdrant runs in local-embedded mode (on-disk, no server) when QDRANT_URL
isn't set — that's only for local dev without the full Docker stack up.
In production (QDRANT_URL set) it talks to a real Qdrant service, which
also means the container filesystem is disposable: the BM25 pickle is
rebuilt from Qdrant's payloads on first use if it isn't already on disk,
so a fresh deploy doesn't need a persistent volume just to keep lexical
search working.
"""

from __future__ import annotations

import os
import pickle
import re
from dataclasses import asdict
from typing import TYPE_CHECKING

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm
from rank_bm25 import BM25Okapi

from app.embeddings import EMBEDDING_DIM
from app.query_translate import detect_lang, translate_query

if TYPE_CHECKING:
    # Only needed for the index_chunks() type hint (deferred by `from
    # __future__ import annotations` above) — importing it for real would
    # pull in app.ingestion.pdf_extract -> PyMuPDF, a heavy ingestion-only
    # dependency that the slim production API image doesn't install.
    from app.ingestion.chunk import Chunk

_QDRANT_PATH = "infra/qdrant-local"
_BM25_PATH = "infra/bm25_index.pkl"
COLLECTION = "regulatory_chunks"

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def get_qdrant_client() -> QdrantClient:
    qdrant_url = os.environ.get("QDRANT_URL")
    if qdrant_url:
        # qdrant-client defaults port=6333 and applies it even when the URL
        # has no explicit port, overriding the scheme's implicit port (443
        # for https) — breaks against a reverse-proxied host like Railway's
        # public domain, which only exposes 443. port=None lets the URL's
        # own scheme decide.
        return QdrantClient(url=qdrant_url, api_key=os.environ.get("QDRANT_API_KEY"), port=None)
    os.makedirs(_QDRANT_PATH, exist_ok=True)
    return QdrantClient(path=_QDRANT_PATH)


def ping_qdrant() -> None:
    """Make a lightweight remote request so an idle Qdrant stays responsive."""
    if not os.environ.get("QDRANT_URL"):
        return
    client = get_qdrant_client()
    try:
        client.get_collection(COLLECTION)
    finally:
        client.close()


def ensure_collection(client: QdrantClient) -> None:
    if not client.collection_exists(COLLECTION):
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=qm.VectorParams(size=EMBEDDING_DIM, distance=qm.Distance.COSINE),
        )


def index_chunks(chunks: list[Chunk], vectors: list[list[float]]) -> None:
    client = get_qdrant_client()
    ensure_collection(client)

    points = [
        qm.PointStruct(
            id=chunk.id,
            vector=vector,
            payload={
                "document": chunk.document,
                "chapter": chunk.chapter,
                "article_num": chunk.article_num,
                "article_title": chunk.article_title,
                "text": chunk.text,
                "page_start": chunk.page_start,
                "page_end": chunk.page_end,
                "part": chunk.part,
                "parts_total": chunk.parts_total,
            },
        )
        for chunk, vector in zip(chunks, vectors)
    ]
    client.upsert(collection_name=COLLECTION, points=points)

    # BM25 index: rebuild from whatever's already indexed + this batch, so
    # re-running ingestion on a new document extends rather than overwrites.
    corpus = _load_bm25_corpus()
    corpus.extend([asdict(c) for c in chunks])
    _save_bm25_corpus(corpus)


def _load_bm25_corpus() -> list[dict]:
    if not os.path.exists(_BM25_PATH):
        return []
    with open(_BM25_PATH, "rb") as f:
        return pickle.load(f)


def _save_bm25_corpus(corpus: list[dict]) -> None:
    os.makedirs(os.path.dirname(_BM25_PATH), exist_ok=True)
    with open(_BM25_PATH, "wb") as f:
        pickle.dump(corpus, f)


_PAYLOAD_FIELDS = [
    "document",
    "chapter",
    "article_num",
    "article_title",
    "text",
    "page_start",
    "page_end",
    "part",
    "parts_total",
]


def rebuild_bm25_from_qdrant() -> list[dict]:
    """Scroll every point's payload out of Qdrant and rebuild the BM25
    pickle from it. Qdrant is the durable store; the pickle is just a
    local cache of the same text for the lexical side of the search."""
    client = get_qdrant_client()
    if not client.collection_exists(COLLECTION):
        return []

    corpus: list[dict] = []
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=COLLECTION, limit=256, offset=offset, with_payload=True
        )
        corpus.extend(
            {"id": p.id, **{field: p.payload.get(field) for field in _PAYLOAD_FIELDS}} for p in points
        )
        if offset is None:
            break

    _save_bm25_corpus(corpus)
    return corpus


def _bm25():
    corpus = _load_bm25_corpus()
    if not corpus:
        corpus = rebuild_bm25_from_qdrant()
    tokenized = [_tokenize(c["text"]) for c in corpus]
    return BM25Okapi(tokenized) if tokenized else None, corpus


def semantic_search(query_vector: list[float], top_k: int = 10) -> list[dict]:
    client = get_qdrant_client()
    if not client.collection_exists(COLLECTION):
        return []
    hits = client.query_points(
        collection_name=COLLECTION, query=query_vector, limit=top_k
    ).points
    return [{"score": h.score, **h.payload, "id": h.id} for h in hits]


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    bm25, corpus = _bm25()
    if bm25 is None:
        return []
    scores = bm25.get_scores(_tokenize(query))
    ranked = sorted(zip(corpus, scores), key=lambda x: x[1], reverse=True)[:top_k]
    return [{"score": float(score), **chunk} for chunk, score in ranked if score > 0]


_BILINGUAL_CODE_DOCUMENTS = {"jo_1609_fr", "jo_1609_ar"}


def _deduplicate_bilingual_provisions(ranked: list[dict], query_lang: str) -> list[dict]:
    """Keep one language version when the same Code article ranks twice."""
    preferred_document = "jo_1609_ar" if query_lang == "ar" else "jo_1609_fr"
    retained: list[dict] = []
    positions: dict[tuple[str, str], int] = {}

    for hit in ranked:
        document = hit.get("document")
        article_num = hit.get("article_num")
        if document not in _BILINGUAL_CODE_DOCUMENTS or not article_num:
            retained.append(hit)
            continue

        key = ("jo_1609", str(article_num))
        existing_position = positions.get(key)
        if existing_position is None:
            positions[key] = len(retained)
            retained.append(hit)
        elif document == preferred_document:
            retained[existing_position] = hit

    return retained


def hybrid_search(
    query: str,
    query_vector: list[float],
    top_k: int = 7,
    translated_query: str | None = None,
) -> list[dict]:
    """Reciprocal Rank Fusion of semantic + lexical results.

    Seven final candidates preserve enough room for multi-article legal
    questions without encouraging the answer model to cite a broad set of
    merely adjacent provisions.

    The corpus is bilingual FR/AR. BM25 only ever matches a query against
    same-language text, so an Arabic query's lexical pass is blind to the
    French documents (and vice versa) — those chunks then only get a
    semantic-side boost while same-language chunks get boosted twice,
    silently burying cross-lingual relevant content under same-language
    noise. Also running the lexical pass on a translated copy of the query
    gives both halves of the corpus a fair lexical signal.
    """
    semantic = semantic_search(query_vector, top_k=30)
    lexical_lists = [lexical_search(query, top_k=30)]

    other_lang = "fr" if detect_lang(query) == "ar" else "ar"
    translated = (
        translate_query(query, other_lang)
        if translated_query is None
        else translated_query
    )
    if translated:
        lexical_lists.append(lexical_search(translated, top_k=30))

    k = 60  # standard RRF constant
    fused: dict[str, float] = {}
    by_id: dict[str, dict] = {}
    for rank, hit in enumerate(semantic):
        fused[hit["id"]] = fused.get(hit["id"], 0) + 1 / (k + rank + 1)
        by_id[hit["id"]] = hit
    for lexical in lexical_lists:
        for rank, hit in enumerate(lexical):
            fused[hit["id"]] = fused.get(hit["id"], 0) + 1 / (k + rank + 1)
            by_id.setdefault(hit["id"], hit)

    ranked_ids = sorted(fused, key=fused.get, reverse=True)
    ranked = [{"rrf_score": fused[i], **by_id[i]} for i in ranked_ids]
    return _deduplicate_bilingual_provisions(ranked, detect_lang(query))[:top_k]
