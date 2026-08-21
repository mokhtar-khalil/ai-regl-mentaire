"""Generate concise, sourced legal answers with a deterministic layout."""

from __future__ import annotations

import os
import re

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from app.documents import label_for
from app.query_translate import detect_lang

DEFAULT_GENERATION_MODEL = "gemini-flash-latest"

_SYSTEM_PROMPT = """Tu es un assistant juridique documentaire. Réponds exclusivement à partir des extraits numérotés fournis. Ta priorité est : fidélité aux sources, réponse exacte à la question, puis clarté. Une réponse partielle mais parfaitement fondée vaut mieux qu'une réponse large comportant des suppositions.

LANGUE — le corpus est bilingue français/arabe
1. {language_rule} Traduis fidèlement le contenu utile des extraits et ne change jamais de langue en cours de réponse.
2. Utilise les extraits pertinents indépendamment de leur langue d'origine.

PÉRIMÈTRE ET PERTINENCE
3. Réponds uniquement à la question posée. N'ajoute pas un panorama général du droit applicable et n'aborde pas un thème voisin simplement parce qu'un extrait le mentionne.
4. Pour une question simple, donne une conclusion courte et un à trois points déterminants. Pour une question large, retiens au maximum quatre points réellement structurants.
5. Chaque point doit apporter un élément nécessaire à la réponse. Écarte les informations seulement contextuelles, institutionnelles ou accessoires.
6. Ne cite normalement pas plus de quatre extraits distincts. Dépasse cette limite uniquement si plusieurs dispositions sont indispensables pour résoudre la question.

SOURCES
7. Pour chaque partie de la réponse, renseigne source_indices uniquement avec les numéros des extraits qui prouvent directement l'affirmation. Un extrait lié au même thème mais qui ne prouve pas l'affirmation ne doit jamais être cité.
8. N'insère aucun marqueur [n] dans summary, title ou text : l'application ajoute les citations de manière déterministe à partir de source_indices.
9. N'écris jamais le nom du document ni une section « Sources » : l'application affiche séparément les références utilisées.

FIDÉLITÉ ET GESTION DE L'INCERTITUDE
10. N'invente aucune information absente des extraits : montant, délai, seuil, sanction, autorité ou procédure. Si une information manque, distingue précisément ce qui est établi de ce qui ne peut pas être déterminé.
11. Ne sois jamais plus affirmatif que la source. Les termes absolus comme « toujours », « obligatoirement », « interdit », « nul » ou « de plein droit » ne sont permis que si le texte les justifie directement.
12. Ne conclus jamais à l'absence d'une règle parce que les extraits n'en parlent pas. Écris que les dispositions récupérées ne permettent pas de l'établir.
13. Distingue la règle explicitement énoncée, son application raisonnée au cas soumis et l'information absente du corpus.
14. Si plusieurs extraits sont indispensables, articule-les. Si deux extraits se contredisent sans règle permettant de trancher, signale l'incertitude.
15. Si la question dépasse le corpus indexé, indique clairement la limite sans généraliser.

STYLE
16. Style clair, professionnel et accessible à un non-juriste. Phrases courtes, pas de préambule, pas de répétition entre le résumé et les points d'analyse.
17. Le résumé donne immédiatement la conclusion en deux à quatre phrases. Les key_points réunissent la règle, son fondement juridique et son explication dans un même point, sans créer trois sections répétitives.
18. Les caveats contiennent uniquement une exception, une limite importante ou une incertitude réelle. Laisse cette liste vide si aucune n'est nécessaire. N'ajoute jamais automatiquement « Aucune autre exception... ».
19. N'utilise pas de généralisation comme « généralement », « en pratique » ou « habituellement » sauf si un extrait l'énonce."""


class _AnswerPoint(BaseModel):
    title: str = Field(description="Intitulé court et professionnel du point")
    text: str = Field(description="Règle et explication directement utiles à la question")
    source_indices: list[int] = Field(
        description="Numéros des seuls extraits qui prouvent directement ce point"
    )


class _StructuredAnswer(BaseModel):
    summary: str = Field(description="Conclusion directe en deux à quatre phrases")
    summary_source_indices: list[int] = Field(
        description="Numéros des extraits qui prouvent directement le résumé"
    )
    key_points: list[_AnswerPoint] = Field(
        description="Un à quatre points déterminants, aucun développement hors sujet"
    )
    caveats: list[_AnswerPoint] = Field(
        description="Zéro à deux exceptions, limites ou incertitudes importantes"
    )


_CITATION_RE = re.compile(r"\[\d+\]")

_HEADINGS = {
    "fr": ("Réponse synthétique", "Analyse juridique", "Points de vigilance"),
    "ar": ("الخلاصة", "التحليل القانوني", "نقاط الانتباه"),
}


def _format_context(numbered_chunks: list[tuple[int, dict]]) -> str:
    parts = []
    for n, c in numbered_chunks:
        label = label_for(c.get("document"))
        article_num = c.get("article_num")
        # "3.2" (World Bank-style numbered paragraph, restarts per section,
        # not a unique id on its own) vs "29" (BCM-style article number).
        ref_word = "§" if article_num and "." in article_num else "Article"
        ref = f"{label}, {ref_word} {article_num}" if article_num else label
        if c.get("chapter"):
            ref += f" ({c['chapter']})"
        parts.append(
            f"[{n}] ({ref}, p.{c.get('page_start')}-{c.get('page_end')})\n{c.get('text')}"
        )
    return "\n\n".join(parts)


_NO_CHUNKS_MESSAGE = {
    "fr": "Aucun extrait pertinent n'a été trouvé dans le corpus indexé pour répondre à cette question.",
    "ar": "لم يتم العثور على مقتطفات ذات صلة في مجموعة الوثائق المفهرسة للإجابة على هذا السؤال.",
}

_LANGUAGE_RULES = {
    None: "Réponds TOUJOURS dans la langue de la question.",
    "fr": "Réponds TOUJOURS en français, quelle que soit la langue de la question.",
    "ar": "أجب دائمًا باللغة العربية، بغض النظر عن لغة السؤال.",
}


def _clean_text(text: str) -> str:
    """Remove model-authored citation markers; citations come from typed indices."""
    cleaned = " ".join(_CITATION_RE.sub("", text or "").split()).strip()
    return re.sub(r"\s+([.,;:!?])", r"\1", cleaned)


def _valid_source_indices(indices: list[int], chunk_count: int) -> list[int]:
    return [
        index
        for index in dict.fromkeys(indices)
        if isinstance(index, int) and 1 <= index <= chunk_count
    ]


def _with_citations(text: str, indices: list[int], chunk_count: int) -> str:
    cleaned = _clean_text(text)
    citations = "".join(f"[{index}]" for index in _valid_source_indices(indices, chunk_count))
    return f"{cleaned} {citations}".strip()


def _format_answer(
    generated: _StructuredAnswer,
    *,
    language: str,
    chunk_count: int,
) -> str:
    summary_heading, analysis_heading, caveats_heading = _HEADINGS[language]
    blocks = [
        f"**{summary_heading}**",
        _with_citations(
            generated.summary,
            generated.summary_source_indices,
            chunk_count,
        ),
    ]

    if generated.key_points:
        blocks.append(f"**{analysis_heading}**")
        blocks.append(
            "\n".join(
                f"- **{_clean_text(point.title).rstrip('.:')}** — "
                f"{_with_citations(point.text, point.source_indices, chunk_count)}"
                for point in generated.key_points[:4]
                if _clean_text(point.text)
            )
        )

    if generated.caveats:
        blocks.append(f"**{caveats_heading}**")
        blocks.append(
            "\n".join(
                f"- **{_clean_text(point.title).rstrip('.:')}** — "
                f"{_with_citations(point.text, point.source_indices, chunk_count)}"
                for point in generated.caveats[:2]
                if _clean_text(point.text)
            )
        )

    return "\n\n".join(block for block in blocks if block.strip())


def answer(question: str, chunks: list[dict], target_lang: str | None = None) -> str:
    if not chunks:
        language = target_lang or detect_lang(question)
        return _NO_CHUNKS_MESSAGE.get(language, _NO_CHUNKS_MESSAGE["fr"])

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    numbered = list(enumerate(chunks, start=1))
    context = _format_context(numbered)
    prompt = f"Extraits réglementaires :\n\n{context}\n\n---\n\nQuestion : {question}"
    system_prompt = _SYSTEM_PROMPT.format(
        language_rule=_LANGUAGE_RULES.get(target_lang, _LANGUAGE_RULES[None])
    )

    response = client.models.generate_content(
        model=os.getenv("GENERATION_MODEL", DEFAULT_GENERATION_MODEL),
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.15,
            response_mime_type="application/json",
            response_schema=_StructuredAnswer,
        ),
    )
    generated = response.parsed
    if not isinstance(generated, _StructuredAnswer):
        generated = _StructuredAnswer.model_validate_json(response.text)

    language = target_lang or detect_lang(question)
    return _format_answer(generated, language=language, chunk_count=len(chunks))
