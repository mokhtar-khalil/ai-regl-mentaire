import { Source } from "@/lib/types";
import { UI_STRINGS } from "@/lib/lang";

export function SourceList({
  sources,
  lang,
  activeIndex,
}: {
  sources: Source[];
  lang: "fr" | "ar";
  activeIndex: number | null;
}) {
  const t = UI_STRINGS[lang];
  if (sources.length === 0) return null;

  return (
    <div className="mt-3 flex flex-wrap gap-1.5" dir={lang === "ar" ? "rtl" : "ltr"}>
      {sources.map((s) => {
        const refWord = s.article_num && s.article_num.includes(".") ? t.section : t.article;
        const isActive = activeIndex === s.index;
        return (
          <div
            key={s.index}
            id={`source-${s.index}`}
            className={`flex min-w-0 max-w-[260px] items-start gap-1.5 rounded-lg border px-2 py-1.5 text-[11.5px] leading-snug transition-colors ${
              isActive
                ? "border-accent bg-accent-soft"
                : "border-line bg-surface"
            }`}
          >
            <span className="mt-px shrink-0 font-mono text-[10px] font-semibold text-accent">[{s.index}]</span>
            <span className="min-w-0 text-ink-soft">
              <span className="text-ink">{s.document_label}</span>
              {s.article_num && (
                <>
                  {" · "}
                  {refWord} {s.article_num}
                </>
              )}
              {s.page_start && (
                <>
                  {" · "}
                  {t.page} {s.page_start}
                  {s.page_end && s.page_end !== s.page_start ? `–${s.page_end}` : ""}
                </>
              )}
            </span>
          </div>
        );
      })}
    </div>
  );
}
