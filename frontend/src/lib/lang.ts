const ARABIC_RE = /[؀-ۿ]/;

export function detectLang(text: string): "fr" | "ar" {
  return ARABIC_RE.test(text) ? "ar" : "fr";
}

export const UI_STRINGS = {
  fr: {
    article: "Article",
    section: "§",
    page: "p.",
    score: "score",
    sources: "Références utilisées",
    noSources: "Aucune source retenue.",
  },
  ar: {
    article: "المادة",
    section: "الفقرة",
    page: "ص.",
    score: "درجة الصلة",
    sources: "المراجع المستخدمة",
    noSources: "لم يتم العثور على مصادر.",
  },
} as const;
