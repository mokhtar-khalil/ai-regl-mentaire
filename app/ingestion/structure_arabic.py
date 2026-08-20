"""Parse OCR'd Arabic legal text: "المادة N" / "المادة الأولى" (Article N /
Article premier) articles under "الباب N" (Titre/Chapitre N) headings.
Mirrors structure.py's French-convention parser but for the Arabic JO,
whose native PDF text extraction comes out with scrambled RTL character
order (numbers glued to the wrong words) — this module only ever runs on
Gemini-vision-OCR'd text, which preserves correct logical reading order.
"""

from __future__ import annotations

import re

from app.ingestion.structure import Article

_CHAPTER_RE = re.compile(r"^#{0,3}[ \t]*\*{0,2}(الباب[ \t]+\S+[ \t]*[-:][ \t]*.*)$", re.MULTILINE)
_ARTICLE_RE = re.compile(
    r"^#{0,3}[ \t]*\*{0,2}المادة[ \t]+(الأولى|\d+)[ \t]*:?\*{0,2}[ \t]*(.*)$", re.MULTILINE
)


def _page_at(page_offsets: list[tuple[int, int]], offset: int) -> int:
    for end, num in page_offsets:
        if offset < end:
            return num
    return page_offsets[-1][1] if page_offsets else 1


def parse_arabic_articles(document_name: str, pages: list[tuple[int, str]]) -> list[Article]:
    full_text = ""
    page_offsets: list[tuple[int, int]] = []
    for page_num, text in pages:
        full_text += text.strip() + "\n\n"
        page_offsets.append((len(full_text), page_num))

    article_matches = list(_ARTICLE_RE.finditer(full_text))
    if not article_matches:
        return []

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
        # Unlike native-extracted French text, each OCR'd Arabic article is
        # often a single flowing line — its content lives in group(2), not
        # in whatever (if anything) follows on the next line. So the body
        # must start from the match itself, not m.end().
        start = m.start()
        end = article_matches[i + 1].start() if i + 1 < len(article_matches) else len(full_text)
        raw_body = full_text[start:end].strip()
        body = "\n".join(
            l for l in raw_body.split("\n") if not _CHAPTER_RE.match(l.strip())
        ).strip()
        body = re.sub(
            r"^#{0,3}[ \t]*\*{0,2}المادة[ \t]+(?:الأولى|\d+)[ \t]*:?\*{0,2}[ \t]*",
            "",
            body,
            count=1,
        )

        article_num = m.group(1).strip()
        title = m.group(2).strip()[:120]

        articles.append(
            Article(
                document=document_name,
                chapter=chapter_before(m.start()),
                article_num=article_num,
                title=title,
                text=body,
                page_start=_page_at(page_offsets, m.start()),
                page_end=_page_at(page_offsets, max(end - 1, m.start())),
                order=i,
            )
        )
    return articles
