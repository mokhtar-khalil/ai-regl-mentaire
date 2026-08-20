"""Cross-lingual query support for the FR/AR corpus.

BM25 is monolingual: an Arabic query scores ~0 against French chunks (no
term overlap), so those chunks only ever reach the results via the
semantic side of the RRF fusion — while same-language chunks get boosted
by *both* signals. That structurally buries relevant French content under
Arabic noise (or vice versa) regardless of actual relevance. Translating
the query into the corpus's other language before lexical search gives
BM25 a fair shot at both halves of the corpus.
"""

from __future__ import annotations

import os
import re

from google import genai
from google.genai import types

TRANSLATE_MODEL = "gemini-flash-latest"
_ARABIC_RE = re.compile(r"[؀-ۿ]")


def detect_lang(text: str) -> str:
    return "ar" if _ARABIC_RE.search(text) else "fr"


def translate_query(text: str, target_lang: str) -> str:
    """Translate a search query for lexical retrieval only — best-effort,
    never shown to the user, never used as the basis for an answer."""
    target_name = "arabe" if target_lang == "ar" else "français"
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    try:
        resp = client.models.generate_content(
            model=TRANSLATE_MODEL,
            contents=f"Traduis cette requête de recherche juridique en {target_name}. "
            f"Réponds uniquement avec la traduction, rien d'autre.\n\n{text}",
            config=types.GenerateContentConfig(temperature=0.0),
        )
        return (resp.text or "").strip()
    except Exception:
        return ""
