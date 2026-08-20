"""Manual inspection script: run the parser on a PDF and print a sample of
the extracted articles, to eyeball quality before wiring up chunking/embeddings.

Usage: .venv/bin/python scripts/inspect_ingestion.py data/Reglement_BCM_Corrige.pdf
"""

import sys

from app.ingestion.pdf_extract import extract_pages
from app.ingestion.structure import parse_articles

path = sys.argv[1]
pages = extract_pages(path)
articles = parse_articles(document_name=path, pages=pages)

print(f"{len(pages)} pages -> {len(articles)} articles\n")

for a in articles[:5]:
    print("=" * 80)
    print(f"[{a.chapter}] Article {a.article_num}: {a.title}  (p.{a.page_start}-{a.page_end})")
    print(a.text[:400])
    print()

print("...")
for a in articles[-2:]:
    print("=" * 80)
    print(f"[{a.chapter}] Article {a.article_num}: {a.title}  (p.{a.page_start}-{a.page_end})")
    print(a.text[:400])

lengths = [len(a.text) for a in articles]
print(f"\nchar length: min={min(lengths)} max={max(lengths)} avg={sum(lengths)//len(lengths)}")
