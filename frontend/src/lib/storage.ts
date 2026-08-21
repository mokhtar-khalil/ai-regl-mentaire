import { Conversation } from "./types";

const KEY = "rag-reglementaire:conversations";

export function loadConversations(): Conversation[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as Conversation[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveConversations(conversations: Conversation[]): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(KEY, JSON.stringify(conversations));
  } catch {
    // Storage full or unavailable (private browsing) — conversation history
    // just won't persist across reloads; not worth surfacing as an error.
  }
}

export function titleFromMessage(text: string): string {
  const trimmed = text.trim().replace(/\s+/g, " ");
  return trimmed.length > 48 ? trimmed.slice(0, 48) + "…" : trimmed;
}
