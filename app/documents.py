"""Registry of ingested documents: id -> human-readable label used in
citations and the sources list. Keeps "bcm" out of the user-facing answer."""

DOCUMENT_LABELS: dict[str, str] = {
    "bcm": "Règlement des marchés de la BCM (2026)",
    "jo_1609_fr": "Journal Officiel n°1609 du 15/07/2026 — Code de la Commande Publique",
    "wb_procurement": "Règlement de Passation des Marchés pour les Emprunteurs sollicitant un FPI (Banque Mondiale, février 2025)",
    "jo_1609_ar": "الجريدة الرسمية رقم 1609 بتاريخ 15/07/2026 — مدونة الطلبية العمومية (Journal Officiel n°1609, version arabe — Code de la Commande Publique)",
}


def label_for(document_id: str) -> str:
    return DOCUMENT_LABELS.get(document_id, document_id)
