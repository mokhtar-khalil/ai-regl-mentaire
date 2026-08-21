"use client";

export function LanguageToggle({
  value,
  onChange,
}: {
  value: "fr" | "ar";
  onChange: (lang: "fr" | "ar") => void;
}) {
  return (
    <div className="flex rounded-full border border-line bg-surface p-0.5">
      {(["fr", "ar"] as const).map((lang) => (
        <button
          key={lang}
          type="button"
          onClick={() => onChange(lang)}
          aria-pressed={value === lang}
          className={`rounded-full px-3 py-1 font-mono text-[11px] font-medium transition-colors ${
            value === lang ? "bg-accent text-white" : "text-ink-soft hover:text-ink"
          }`}
        >
          {lang === "fr" ? "Français" : "العربية"}
        </button>
      ))}
    </div>
  );
}
