"""Parse a term/definition markdown-table glossary (as produced by OCR) into
Article-compatible records — one per term, article_num=None since terms
aren't numbered, chapter fixed to the glossary's own heading."""

from __future__ import annotations

import re

from app.ingestion.structure import Article

_ROW_RE = re.compile(r"^\|(.+)\|$")
_SEPARATOR_RE = re.compile(r"^[\s|:-]+$")


def _clean_cell(text: str) -> str:
    text = text.strip().strip("*").strip()
    text = text.replace("<br><br>", "\n\n").replace("<br>", "\n")
    return text


def parse_glossary(document_name: str, chapter: str, pages: list[tuple[int, str]]) -> list[Article]:
    entries: list[Article] = []
    current: Article | None = None

    for page_num, text in pages:
        for line in text.split("\n"):
            m = _ROW_RE.match(line.strip())
            if not m:
                continue
            cells = [c.strip() for c in m.group(1).split("|")]
            if len(cells) != 2:
                continue
            if _SEPARATOR_RE.match(cells[0]) and _SEPARATOR_RE.match(cells[1]):
                continue
            term, definition = _clean_cell(cells[0]), _clean_cell(cells[1])
            if term.lower().startswith("sigle ou abr"):
                continue  # repeated header row

            if term:
                if current:
                    entries.append(current)
                current = Article(
                    document=document_name,
                    chapter=chapter,
                    article_num=None,
                    title=term,
                    text=f"{term} : {definition}",
                    page_start=page_num,
                    page_end=page_num,
                    order=len(entries),
                )
            elif current:
                # Continuation row: this entry's definition wrapped onto a
                # new markdown table row on the next page, term cell blank.
                current.text += " " + definition
                current.page_end = page_num

    if current:
        entries.append(current)
    return entries
