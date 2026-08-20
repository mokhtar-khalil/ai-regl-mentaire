"""Ingest the OCR'd Arabic Code de la Commande Publique.

Usage:
  .venv/bin/python scripts/ingest_arabic.py infra/ocr_cache/jo_1609_ar jo_1609_ar --pages 3:18
"""

import sys

from dotenv import load_dotenv

load_dotenv(".env")

from app.embeddings import embed_texts
from app.index_store import index_chunks
from app.ingestion.chunk import chunk_articles
from app.ingestion.structure_arabic import parse_arabic_articles

cache_dir = sys.argv[1]
document_name = sys.argv[2]
start, end = (int(x) for x in sys.argv[sys.argv.index("--pages") + 1].split(":"))

pages = []
for i in range(start, end + 1):
    with open(f"{cache_dir}/{i}.md", encoding="utf-8") as f:
        pages.append((i, f.read()))
print(f"{len(pages)} pages")

articles = parse_arabic_articles(document_name, pages)
print(f"{len(articles)} articles")

chunks = chunk_articles(articles)
print(f"{len(chunks)} chunks")

print(f"Embedding {len(chunks)} chunks via Gemini text-embedding-004...")
vectors = embed_texts([c.text for c in chunks])
print(f"  {len(vectors)} vectors")

print("Indexing (Qdrant semantic + BM25 lexical)...")
index_chunks(chunks, vectors)
print("Done.")
