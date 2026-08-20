"""Gradio front-end for the RAG Réglementaire API.

Talks to the FastAPI backend over HTTP (app/main.py) — start that first:
  PYTHONPATH=. .venv/bin/uvicorn app.main:app --port 8000
  PYTHONPATH=. .venv/bin/python gradio_app.py
"""

import os
import sys

import gradio as gr
import requests

sys.path.insert(0, os.path.dirname(__file__))
from app.query_translate import detect_lang

API_URL = os.environ.get("RAG_API_URL", "http://127.0.0.1:8000")

# The answer's language decides both text direction and which set of
# labels wraps the sources list — a French "Article 29 — p. 15" reads as
# noise glued onto an Arabic answer, and left-aligned Arabic reads wrong.
_LABELS = {
    "fr": {
        "article": "Article",
        "section": "§",
        "page": "p.",
        "score": "score",
        "no_sources": "_Aucune source retenue._",
        "sources_header": "### Sources récupérées (RRF)",
    },
    "ar": {
        "article": "المادة",
        "section": "الفقرة",
        "page": "ص.",
        "score": "درجة الصلة",
        "no_sources": "_لم يتم العثور على مصادر._",
        "sources_header": "### المصادر المسترجعة",
    },
}


def ask(question: str, top_k: int):
    if not question.strip():
        return gr.update(value="", rtl=False), gr.update(value="### Sources récupérées (RRF)", rtl=False)

    resp = requests.post(f"{API_URL}/ask", json={"question": question, "top_k": int(top_k)}, timeout=120)
    resp.raise_for_status()
    data = resp.json()

    is_rtl = detect_lang(data["answer"]) == "ar"
    labels = _LABELS["ar"] if is_rtl else _LABELS["fr"]

    def ref_label(num):
        # "3.2" (World Bank-style numbered paragraph, not globally unique —
        # duplicated across sections) vs "29" (BCM-style article number).
        return labels["section"] if num and "." in num else labels["article"]

    if data["sources"]:
        sources_md = "\n\n".join(
            f"**[{s['index']}]** {s['document_label']}"
            + (f" — {s['chapter']}" if s.get("chapter") else "")
            + (f", {ref_label(s.get('article_num'))} {s['article_num']}" if s.get("article_num") else "")
            + (f" — *{s['article_title']}*" if s.get("article_title") else "")
            + f"  \n{labels['page']} {s.get('page_start')}–{s.get('page_end')} · {labels['score']} {round(s.get('rrf_score') or 0, 3)}"
            for s in data["sources"]
        )
    else:
        sources_md = labels["no_sources"]
    sources_md = f"{labels['sources_header']}\n\n{sources_md}"

    return gr.update(value=data["answer"], rtl=is_rtl), gr.update(value=sources_md, rtl=is_rtl)


with gr.Blocks(title="RAG Réglementaire — test") as demo:
    gr.Markdown("# RAG Réglementaire — banc de test\nAppelle l'API FastAPI (`/ask`) : retrieval hybride + génération sourcée.")

    with gr.Row():
        with gr.Column(scale=2):
            question = gr.Textbox(
                label="Question",
                placeholder="Ex. Quels sont les seuils de passation des marchés de la BCM ?",
                lines=2,
            )
            top_k = gr.Slider(label="Nombre de chunks retenus", minimum=2, maximum=20, value=10, step=1)
            submit = gr.Button("Poser la question", variant="primary")
            response = gr.Markdown()

        with gr.Column(scale=1):
            sources = gr.Markdown("### Sources récupérées (RRF)")

    submit.click(ask, inputs=[question, top_k], outputs=[response, sources])
    question.submit(ask, inputs=[question, top_k], outputs=[response, sources])

if __name__ == "__main__":
    demo.launch()
