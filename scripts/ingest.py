"""Ingest a PDF end-to-end: parse -> chunk -> embed -> index (semantic + lexical).

A JO (Journal Officiel) issue is a bulletin bundling several unrelated legal
instruments (a law, then decrees, appointments, dissolution notices...) with
article numbering that restarts for each one. Ingesting the whole bulletin as
a single "document" collides article numbers and pollutes the index with
one-off administrative acts. Use --pages start:end (1-indexed, inclusive) to
scope ingestion to the one instrument that's actually regulatory content.

Usage:
  .venv/bin/python scripts/ingest.py data/Reglement_BCM_Corrige.pdf bcm
  .venv/bin/python scripts/ingest.py "data/J.O. 1609F DU 15.07.2026 (1)2.pdf" jo_1609_fr --pages 3:26
"""

import sys

from dotenv import load_dotenv

load_dotenv()

from app.embeddings import embed_texts
from app.index_store import index_chunks
from app.ingestion.chunk import chunk_articles
from app.ingestion.pdf_extract import extract_pages
from app.ingestion.structure import parse_articles

pdf_path = sys.argv[1]
document_name = sys.argv[2] if len(sys.argv) > 2 else pdf_path

page_range = None
if "--pages" in sys.argv:
    spec = sys.argv[sys.argv.index("--pages") + 1]
    start, end = (int(x) for x in spec.split(":"))
    page_range = (start, end)

print(f"Extracting pages from {pdf_path}...")
pages = extract_pages(pdf_path)
if page_range:
    pages = [p for p in pages if page_range[0] <= p.number <= page_range[1]]
print(f"  {len(pages)} pages" + (f" (scoped to {page_range[0]}-{page_range[1]})" if page_range else ""))

print("Parsing articles...")
articles = parse_articles(document_name, pages)
print(f"  {len(articles)} articles")

print("Chunking...")
chunks = chunk_articles(articles)
print(f"  {len(chunks)} chunks")

print(f"Embedding {len(chunks)} chunks via Gemini text-embedding-004...")
vectors = embed_texts([c.text for c in chunks])
print(f"  {len(vectors)} vectors ({len(vectors[0])} dims)")

print("Indexing (Qdrant semantic + BM25 lexical)...")
index_chunks(chunks, vectors)
print("Done.")
