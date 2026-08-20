"""Parse OCR'd text that uses the World Bank convention: "Section N. Title"
headers and numbered paragraphs ("3.7 <text>") rather than BCM-style
"Article N :". Reuses the Article dataclass from structure.py — the chunker
and generator only care about that shape, not which convention produced it.
"""

from __future__ import annotations

import re

from app.ingestion.structure import Article

_SECTION_RE = re.compile(r"^#{0,3}[ \t]*((?:Section|Annexe)[ \t]+[IVXLCDM0-9]+\.?[ \t]*.*)$", re.MULTILINE)
_PARAGRAPH_RE = re.compile(r"^(\d{1,3}\.\d{1,3}(?:\.\d{1,3})?)\s+(.+)$", re.MULTILINE)
# Table-of-contents lines use dot leaders ("Titre .......... 12") — strip
# them before parsing so a TOC entry never gets mistaken for a real section.
_TOC_LINE_RE = re.compile(r"\.{4,}\s*\d*\s*$")


def parse_paragraphs(document_name: str, pages: list[tuple[int, str]]) -> list[Article]:
    """`pages` is [(page_number, ocr_text), ...] as returned by ocr_pdf()."""
    full_text = ""
    page_offsets: list[tuple[int, int]] = []
    for page_num, text in pages:
        kept_lines = [l for l in text.strip().split("\n") if not _TOC_LINE_RE.search(l)]
        full_text += "\n".join(kept_lines) + "\n\n"
        page_offsets.append((len(full_text), page_num))

    def page_at(offset: int) -> int:
        for end, num in page_offsets:
            if offset < end:
                return num
        return page_offsets[-1][1] if page_offsets else 1

    section_matches = list(_SECTION_RE.finditer(full_text))

    def section_before(offset: int) -> str | None:
        current = None
        for m in section_matches:
            if m.start() > offset:
                break
            current = m.group(1).strip()
        return current

    para_matches = list(_PARAGRAPH_RE.finditer(full_text))
    if not para_matches:
        return []

    articles: list[Article] = []
    for i, m in enumerate(para_matches):
        start = m.start()
        end = para_matches[i + 1].start() if i + 1 < len(para_matches) else len(full_text)
        raw_body = full_text[start:end].strip()
        # Drop a section/annexe heading that fell inside this slice (it
        # belongs to the *next* paragraph's context, not this one's text).
        body = "\n".join(
            l for l in raw_body.split("\n") if not _SECTION_RE.match(l.strip())
        ).strip()
        # The paragraph number itself is the first token of raw_body/body.
        body = re.sub(r"^\d{1,3}\.\d{1,3}(?:\.\d{1,3})?\s+", "", body, count=1)

        para_num = m.group(1)
        first_sentence = re.split(r"(?<=[.:])\s", m.group(2).strip(), maxsplit=1)[0]

        articles.append(
            Article(
                document=document_name,
                chapter=section_before(m.start()),
                article_num=para_num,
                title=first_sentence[:120],
                text=body,
                page_start=page_at(m.start()),
                page_end=page_at(max(end - 1, m.start())),
                order=i,
            )
        )
    return articles
