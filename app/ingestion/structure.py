"""Turn extracted pages into article-level chunks with legal metadata.

Tuned for the French "Article N : Titre" / "CHAPITRE X : TITRE" convention
used across the BCM/procurement corpus. Falls back to a single untitled
section if no article markers are found, so it degrades gracefully on
documents that don't follow this convention (handled separately).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.ingestion.pdf_extract import Page

_CHAPTER_RE = re.compile(
    r"^((?:CHAPITRE|TITRE)\s+(?:PRÉLIMINAIRE|[IVXLCDM]+)\s*:?\s*.*)$", re.MULTILINE
)
_ARTICLE_RE = re.compile(
    r"^Article\s+(premier|\d+[a-z]?)\s*:?\s*(.*)$", re.MULTILINE | re.IGNORECASE
)
# Table-of-contents lines use dot leaders ("Titre .......... 15") or end in a
# bare page number; real article/chapter bodies never do. Stripping these
# before parsing keeps the TOC from being mistaken for real articles.
_TOC_LINE_RE = re.compile(r"\.{4,}\s*\d*\s*$")


@dataclass
class Article:
    document: str
    chapter: str | None
    article_num: str | None
    title: str
    text: str
    page_start: int
    page_end: int
    order: int
    metadata: dict = field(default_factory=dict)


def _page_at_offset(page_offsets: list[tuple[int, int]], offset: int) -> int:
    for start, page_num in page_offsets:
        if offset < start:
            return page_num
    return page_offsets[-1][1] if page_offsets else 1


def parse_articles(document_name: str, pages: list[Page]) -> list[Article]:
    full_text = ""
    page_offsets: list[tuple[int, int]] = []  # (end_offset_exclusive, page_number)
    for page in pages:
        kept_lines = [l for l in page.text.split("\n") if not _TOC_LINE_RE.search(l)]
        full_text += "\n".join(kept_lines) + "\n"
        page_offsets.append((len(full_text), page.number))

    article_matches = list(_ARTICLE_RE.finditer(full_text))
    if not article_matches:
        return [
            Article(
                document=document_name,
                chapter=None,
                article_num=None,
                title=document_name,
                text=full_text.strip(),
                page_start=pages[0].number if pages else 1,
                page_end=pages[-1].number if pages else 1,
                order=0,
            )
        ]

    chapter_matches = list(_CHAPTER_RE.finditer(full_text))

    def chapter_before(offset: int) -> str | None:
        current = None
        for m in chapter_matches:
            if m.start() > offset:
                break
            current = m.group(1).strip()
        return current

    articles: list[Article] = []
    for i, m in enumerate(article_matches):
        start = m.end()
        end = article_matches[i + 1].start() if i + 1 < len(article_matches) else len(full_text)
        raw_body = full_text[start:end].strip()
        # A chapter heading for the *next* article can fall inside this
        # slice (it appears after this article's text but before the next
        # "Article" marker) — drop it so it doesn't tail onto this body.
        body = "\n".join(
            l for l in raw_body.split("\n") if not _CHAPTER_RE.match(l.strip())
        ).strip()
        title = m.group(2).strip().rstrip(":").strip()
        article_num = m.group(1).strip()

        start_page = _page_at_offset(page_offsets, m.start())
        end_page = _page_at_offset(page_offsets, max(end - 1, m.start()))

        articles.append(
            Article(
                document=document_name,
                chapter=chapter_before(m.start()),
                article_num=article_num,
                title=title,
                text=body,
                page_start=start_page,
                page_end=end_page,
                order=i,
            )
        )
    return articles
