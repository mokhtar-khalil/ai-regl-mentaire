"""End-to-end query: hybrid retrieval -> sourced generation.

Usage: .venv/bin/python scripts/ask.py "Quels sont les seuils de passation des marchés ?"
"""

import sys

from dotenv import load_dotenv

load_dotenv(".env")

from app.embeddings import embed_query
from app.generate import answer
from app.index_store import hybrid_search

question = sys.argv[1]

query_vector = embed_query(question)
chunks = hybrid_search(question, query_vector, top_k=6)

print(f"--- {len(chunks)} chunks retenus (RRF) ---")
for c in chunks:
    print(f"  [{c.get('rrf_score', 0):.4f}] {c.get('document')} Article {c.get('article_num')}: {c.get('article_title')}")

print("\n--- Réponse ---\n")
print(answer(question, chunks))
