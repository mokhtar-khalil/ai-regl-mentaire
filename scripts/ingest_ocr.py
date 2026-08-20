"""Ingest an already-OCR'd PDF (see scripts/ocr_pdf.py) using the
Section/paragraph-numbering parser: parse -> chunk -> embed -> index.

Usage:
  .venv/bin/python scripts/ingest_ocr.py infra/ocr_cache/wb_procurement wb_procurement --pages 12:157
"""

import glob
import os
import re
import sys

from dotenv import load_dotenv

load_dotenv(".env")

from app.embeddings import embed_texts
from app.index_store import index_chunks
from app.ingestion.chunk import chunk_articles
from app.ingestion.structure_paragraphs import parse_paragraphs

cache_dir = sys.argv[1]
document_name = sys.argv[2]

page_range = None
if "--pages" in sys.argv:
    spec = sys.argv[sys.argv.index("--pages") + 1]
    start, end = (int(x) for x in spec.split(":"))
    page_range = (start, end)

print(f"Loading cached OCR pages from {cache_dir}...")
page_files = sorted(
    glob.glob(os.path.join(cache_dir, "*.md")),
    key=lambda p: int(re.search(r"(\d+)\.md$", p).group(1)),
)
pages = []
for p in page_files:
    num = int(re.search(r"(\d+)\.md$", p).group(1))
    if page_range and not (page_range[0] <= num <= page_range[1]):
        continue
    with open(p, encoding="utf-8") as f:
        pages.append((num, f.read()))
print(f"  {len(pages)} pages" + (f" (scoped to {page_range[0]}-{page_range[1]})" if page_range else ""))

print("Parsing paragraphs...")
articles = parse_paragraphs(document_name, pages)
print(f"  {len(articles)} paragraphs")

print("Chunking...")
chunks = chunk_articles(articles)
print(f"  {len(chunks)} chunks")

print(f"Embedding {len(chunks)} chunks via Gemini text-embedding-004...")
vectors = embed_texts([c.text for c in chunks])
print(f"  {len(vectors)} vectors ({len(vectors[0])} dims)")

print("Indexing (Qdrant semantic + BM25 lexical)...")
index_chunks(chunks, vectors)
print("Done.")
