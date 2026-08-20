"""Split parsed articles into embedding-sized chunks.

Most articles (~1100 chars on average, per BCM corpus) fit in a single
chunk as-is — splitting them further would only hurt retrieval by cutting
a legal provision mid-thought. Only oversized articles (a handful, up to
~10k chars) get split, and only on paragraph boundaries so a chunk never
starts or ends mid-sentence.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from app.ingestion.structure import Article

MAX_CHARS = 1800
MIN_CHARS = 200  # avoid a trailing sliver chunk from a stray short paragraph


@dataclass
class Chunk:
    id: str
    document: str
    chapter: str | None
    article_num: str | None
    article_title: str
    text: str
    page_start: int
    page_end: int
    part: int  # 0 if the article wasn't split, else 1-indexed sub-part
    parts_total: int
    metadata: dict = field(default_factory=dict)


def _split_paragraphs(text: str, max_chars: int) -> list[str]:
    # PyMuPDF's get_text() gives visual line breaks, not blank-line-separated
    # paragraphs, so pack lines greedily instead of splitting on "\n\n" —
    # that keeps breaks at a line boundary (never mid-word) and close to a
    # sentence end most of the time, since legal text lines mostly end there.
    units = [p.strip() for p in text.split("\n\n") if p.strip()]
    if len(units) <= 1:
        units = [l.strip() for l in text.split("\n") if l.strip()]
    if not units:
        units = [text]

    parts: list[str] = []
    current = ""
    for unit in units:
        candidate = f"{current}\n{unit}" if current else unit
        if len(candidate) <= max_chars or not current:
            current = candidate
        else:
            parts.append(current)
            current = unit
    if current:
        parts.append(current)

    # Merge a too-small trailing part into the previous one rather than
    # shipping a near-empty chunk.
    if len(parts) > 1 and len(parts[-1]) < MIN_CHARS:
        parts[-2] = f"{parts[-2]}\n\n{parts[-1]}"
        parts.pop()
    return parts


def chunk_articles(articles: list[Article], max_chars: int = MAX_CHARS) -> list[Chunk]:
    chunks: list[Chunk] = []
    for article in articles:
        parts = (
            [article.text]
            if len(article.text) <= max_chars
            else _split_paragraphs(article.text, max_chars)
        )
        for i, part_text in enumerate(parts):
            chunks.append(
                Chunk(
                    id=str(uuid.uuid4()),
                    document=article.document,
                    chapter=article.chapter,
                    article_num=article.article_num,
                    article_title=article.title,
                    text=part_text,
                    page_start=article.page_start,
                    page_end=article.page_end,
                    part=0 if len(parts) == 1 else i + 1,
                    parts_total=len(parts),
                    metadata=dict(article.metadata),
                )
            )
    return chunks
