"""Ingest a term/definition glossary from cached OCR pages.

Usage:
  .venv/bin/python scripts/ingest_glossary.py infra/ocr_cache/wb_procurement wb_procurement 5:11 "Sigles et abréviations usuels et expressions et termes définis"
"""

import sys

from dotenv import load_dotenv

load_dotenv(".env")

from app.embeddings import embed_texts
from app.index_store import index_chunks
from app.ingestion.chunk import chunk_articles
from app.ingestion.glossary import parse_glossary

cache_dir = sys.argv[1]
document_name = sys.argv[2]
start, end = (int(x) for x in sys.argv[3].split(":"))
chapter = sys.argv[4]

pages = []
for i in range(start, end + 1):
    with open(f"{cache_dir}/{i}.md", encoding="utf-8") as f:
        pages.append((i, f.read()))

print(f"Parsing glossary from {len(pages)} pages...")
entries = parse_glossary(document_name, chapter, pages)
print(f"  {len(entries)} terms")

chunks = chunk_articles(entries)
print(f"  {len(chunks)} chunks")

print(f"Embedding {len(chunks)} chunks via Gemini text-embedding-004...")
vectors = embed_texts([c.text for c in chunks])
print(f"  {len(vectors)} vectors")

print("Indexing (Qdrant semantic + BM25 lexical)...")
index_chunks(chunks, vectors)
print("Done.")
