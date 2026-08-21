"use client";

import { Conversation } from "@/lib/types";

export function Sidebar({
  conversations,
  activeId,
  onSelect,
  onNew,
  onDelete,
}: {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
}) {
  const sorted = [...conversations].sort((a, b) => b.updatedAt - a.updatedAt);

  return (
    <aside className="flex h-dvh w-64 shrink-0 flex-col border-r border-line bg-surface">
      <div className="p-3">
        <button
          type="button"
          onClick={onNew}
          className="flex w-full items-center justify-center gap-2 rounded-xl border border-line bg-paper px-3 py-2 text-[13.5px] font-medium text-ink transition-colors hover:border-accent"
        >
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
            <path d="M8 3v10M3 8h10" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
          </svg>
          Nouvelle conversation
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-3">
        {sorted.length === 0 ? (
          <p className="px-2 py-3 text-[12.5px] text-ink-faint">Aucune conversation pour l&apos;instant.</p>
        ) : (
          <ul className="flex flex-col gap-0.5">
            {sorted.map((c) => (
              <li key={c.id} className="group relative">
                <button
                  type="button"
                  onClick={() => onSelect(c.id)}
                  className={`w-full truncate rounded-lg px-3 py-2 text-left text-[13px] transition-colors ${
                    c.id === activeId ? "bg-accent-soft text-accent-ink" : "text-ink-soft hover:bg-paper"
                  }`}
                >
                  {c.title || "Nouvelle conversation"}
                </button>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(c.id);
                  }}
                  aria-label="Supprimer la conversation"
                  className="absolute right-1.5 top-1/2 hidden -translate-y-1/2 rounded-md p-1 text-ink-faint hover:bg-danger-soft hover:text-danger group-hover:block"
                >
                  <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
                    <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                  </svg>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}
