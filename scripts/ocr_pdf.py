"""OCR a scanned PDF page by page, caching progress to disk (resumable).

Usage:
  .venv/bin/python scripts/ocr_pdf.py "data/Procurement-....pdf" infra/ocr_cache/wb_procurement
"""

import sys

from dotenv import load_dotenv

load_dotenv(".env")

from app.ingestion.ocr import ocr_pdf

pdf_path = sys.argv[1]
cache_dir = sys.argv[2]

results = ocr_pdf(pdf_path, cache_dir)
print(f"Done: {len(results)} pages OCR'd (cached in {cache_dir}/)")
