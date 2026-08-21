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
    <div className="mt-5 border-t border-line pt-3" dir={lang === "ar" ? "rtl" : "ltr"}>
      <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-faint">{t.sources}</p>
      <div className="grid gap-2 sm:grid-cols-2">
        {sources.map((s) => {
          const refWord = s.article_num && s.article_num.includes(".") ? t.section : t.article;
          const isActive = activeIndex === s.index;
          return (
            <div
              key={s.index}
              id={`source-${s.index}`}
              className={`flex min-w-0 items-start gap-2 rounded-lg border px-2.5 py-2 text-[11.5px] leading-snug transition-colors ${
                isActive ? "border-accent bg-accent-soft shadow-sm" : "border-line bg-paper/60"
              }`}
            >
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-accent-soft font-mono text-[10px] font-bold text-accent">
                {s.index}
              </span>
              <span className="min-w-0 text-ink-soft">
                <span className="block font-medium text-ink">{s.document_label}</span>
                <span>
                  {s.article_num && `${refWord} ${s.article_num}`}
                  {s.article_title && ` — ${s.article_title}`}
                  {s.page_start && (
                    <>
                      {s.article_num || s.article_title ? " · " : ""}
                      {t.page} {s.page_start}
                      {s.page_end && s.page_end !== s.page_start ? `–${s.page_end}` : ""}
                    </>
                  )}
                </span>
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
