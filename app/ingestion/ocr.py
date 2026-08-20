"""OCR scanned PDF pages via Gemini vision: full text transcription with
tables reconstructed as markdown. Used for documents with no embedded text
layer (e.g. the World Bank procurement regulations), where a plain-text
OCR engine like Tesseract would flatten tables into unusable noise.

Each page is cached to disk after OCR — a 150+ page document is a real,
non-trivial cost, and a crash or rate limit shouldn't mean re-paying for
pages already done. OCR calls run concurrently (network-bound, not
CPU-bound) since doing 150+ pages one at a time serially is what made the
first run of this take ages.
"""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import fitz
from google import genai
from google.genai import types

OCR_MODEL = "gemini-flash-latest"
RENDER_DPI = 200
MAX_WORKERS = 8

_OCR_PROMPT = """Transcris intégralement cette page de document réglementaire en français, dans l'ordre de lecture naturel.

Règles :
- Reproduis fidèlement tout le texte, y compris les numéros de paragraphe (ex. "3.7"), titres de section, notes de bas de page.
- Si la page contient un TABLEAU, reconstruis-le en tableau markdown (| colonne | ... |), en conservant toutes les lignes et colonnes, y compris les cases à cocher (utilise ✓ et X tels quels) et les cellules fusionnées (répète la valeur si nécessaire pour garder le tableau rectangulaire).
- Si la page contient un schéma, organigramme ou diagramme, transcris le texte de chaque bloc/étape sous forme de liste ordonnée, en indiquant brièvement les flèches/relations entre blocs, plutôt que de décrire l'image visuellement.
- N'ajoute aucun commentaire, résumé ou remarque de ta part : uniquement le contenu transcrit.
- Si la page est vide ou ne contient qu'un numéro de page/en-tête récurrent, réponds juste avec ce texte.

Ne traduis rien, ne corrige pas le fond, ne complète pas les informations manquantes."""


def _client() -> genai.Client:
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def _ocr_image_bytes(client: genai.Client, image_bytes: bytes) -> str:
    for attempt in range(5):
        try:
            resp = client.models.generate_content(
                model=OCR_MODEL,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                    _OCR_PROMPT,
                ],
                config=types.GenerateContentConfig(temperature=0.0),
            )
            return resp.text or ""
        except Exception:
            if attempt == 4:
                raise
            time.sleep(2**attempt)
    return ""


def ocr_page(client: genai.Client, page: fitz.Page) -> str:
    pix = page.get_pixmap(dpi=RENDER_DPI)
    return _ocr_image_bytes(client, pix.tobytes("png"))


def ocr_pdf(
    pdf_path: str,
    cache_dir: str,
    page_range: tuple[int, int] | None = None,
    max_workers: int = MAX_WORKERS,
) -> list[tuple[int, str]]:
    """OCR every page (1-indexed, inclusive range if given), caching each
    page's transcription to `{cache_dir}/{page_num}.md`. Returns
    [(page_number, text), ...] in order. Pages not yet cached are OCR'd
    concurrently — rendering (CPU, via a per-thread fitz.Document) is cheap,
    the Gemini call (network) is the actual bottleneck worth parallelizing."""
    os.makedirs(cache_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    start, end = page_range if page_range else (1, len(doc))
    doc.close()

    todo = []
    cached: dict[int, str] = {}
    for page_num in range(start, end + 1):
        cache_path = os.path.join(cache_dir, f"{page_num}.md")
        if os.path.exists(cache_path):
            with open(cache_path, encoding="utf-8") as f:
                cached[page_num] = f.read()
        else:
            todo.append(page_num)

    print(f"  {len(cached)} pages already cached, {len(todo)} to OCR")

    def _process(page_num: int) -> tuple[int, str]:
        thread_client = _client()
        thread_doc = fitz.open(pdf_path)
        try:
            text = ocr_page(thread_client, thread_doc[page_num - 1])
        finally:
            thread_doc.close()
        cache_path = os.path.join(cache_dir, f"{page_num}.md")
        tmp_path = cache_path + f".tmp{os.getpid()}"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp_path, cache_path)
        return page_num, text

    if todo:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_process, n): n for n in todo}
            done = 0
            for future in as_completed(futures):
                page_num, text = future.result()
                cached[page_num] = text
                done += 1
                print(f"  OCR page {page_num} done ({done}/{len(todo)}, {len(text)} chars)")

    return [(n, cached[n]) for n in range(start, end + 1)]
