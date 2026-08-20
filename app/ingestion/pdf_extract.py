"""Extract per-page text from a PDF, stripping repeated running headers/footers."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

import fitz  # pymupdf


@dataclass
class Page:
    number: int  # 1-indexed, matches the printed page number when detected
    text: str


_PAGE_NUM_RE = re.compile(r"^\d{1,4}$")


def _line_signature(line: str) -> str:
    """Normalize a line so the same running header matches across pages
    even though it carries a different page number each time."""
    return _PAGE_NUM_RE.sub("#", line.strip())


def extract_pages(pdf_path: str) -> list[Page]:
    doc = fitz.open(pdf_path)
    raw_pages = [doc[i].get_text() for i in range(len(doc))]

    # Detect running headers/footers: lines (after normalizing page numbers)
    # that repeat on most pages are boilerplate, not content.
    line_counts: Counter[str] = Counter()
    per_page_lines = []
    for raw in raw_pages:
        lines = [l.strip() for l in raw.split("\n")]
        per_page_lines.append(lines)
        seen = {_line_signature(l) for l in lines if l}
        line_counts.update(seen)

    boilerplate_threshold = max(3, int(len(raw_pages) * 0.5))
    boilerplate = {sig for sig, count in line_counts.items() if count >= boilerplate_threshold}

    pages: list[Page] = []
    for idx, lines in enumerate(per_page_lines):
        kept = [l for l in lines if l and _line_signature(l) not in boilerplate]
        pages.append(Page(number=idx + 1, text="\n".join(kept)))
    return pages
