import unittest

from app.generate import _AnswerPoint, _StructuredAnswer, _format_answer
from app.index_store import _deduplicate_bilingual_provisions
from app.main import _renumber_citations


class AnswerFormattingTests(unittest.TestCase):
    def test_structured_answer_keeps_only_valid_typed_citations(self):
        generated = _StructuredAnswer(
            summary="La règle est établie [99].",
            summary_source_indices=[3, 3, 99],
            key_points=[
                _AnswerPoint(
                    title="Fondement",
                    text="Le texte fixe directement cette règle [8].",
                    source_indices=[3],
                )
            ],
            caveats=[],
        )

        rendered = _format_answer(generated, language="fr", chunk_count=7)

        self.assertIn("La règle est établie. [3]", rendered)
        self.assertIn("Le texte fixe directement cette règle. [3]", rendered)
        self.assertNotIn("[8]", rendered)
        self.assertNotIn("[99]", rendered)

    def test_visible_citations_are_contiguous(self):
        rendered, original_indices = _renumber_citations(
            "Conclusion [4]. Précision [2][4]. Citation invalide [12].",
            [
                {"document": "bcm", "article_num": str(index)}
                for index in range(1, 8)
            ],
        )

        self.assertEqual(original_indices, [4, 2])
        self.assertEqual(rendered, "Conclusion [1]. Précision [2][1]. Citation invalide.")

    def test_split_chunks_of_same_article_share_one_visible_reference(self):
        rendered, original_indices = _renumber_citations(
            "Règle [1][2].",
            [
                {"document": "bcm", "article_num": "premier", "part": 1},
                {"document": "bcm", "article_num": "premier", "part": 2},
            ],
        )

        self.assertEqual(original_indices, [1])
        self.assertEqual(rendered, "Règle [1].")

    def test_same_numbered_paragraph_in_different_chapters_stays_distinct(self):
        rendered, original_indices = _renumber_citations(
            "Première règle [1]. Deuxième règle [2].",
            [
                {"document": "world_bank", "chapter": "I", "article_num": "3.2"},
                {"document": "world_bank", "chapter": "II", "article_num": "3.2"},
            ],
        )

        self.assertEqual(original_indices, [1, 2])
        self.assertEqual(rendered, "Première règle [1]. Deuxième règle [2].")


class RetrievalDeduplicationTests(unittest.TestCase):
    def test_same_code_article_keeps_query_language_version(self):
        ranked = [
            {"id": "fr-2", "document": "jo_1609_fr", "article_num": "2"},
            {"id": "ar-2", "document": "jo_1609_ar", "article_num": "2"},
            {"id": "ar-12", "document": "jo_1609_ar", "article_num": "12"},
        ]

        retained = _deduplicate_bilingual_provisions(ranked, "ar")

        self.assertEqual([hit["id"] for hit in retained], ["ar-2", "ar-12"])


if __name__ == "__main__":
    unittest.main()
