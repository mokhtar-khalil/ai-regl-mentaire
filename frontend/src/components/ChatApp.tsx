"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ChatMessage, AskResponse, Conversation } from "@/lib/types";
import { detectLang } from "@/lib/lang";
import { loadConversations, saveConversations, titleFromMessage } from "@/lib/storage";
import { MessageBubble } from "./MessageBubble";
import { Composer } from "./Composer";
import { Sidebar } from "./Sidebar";
import { LanguageToggle } from "./LanguageToggle";

const EXAMPLE_PROMPTS = [
  { fr: "Quels sont les seuils de passation des marchés de la BCM ?", ar: null },
  { fr: "Quelle est la hiérarchie entre le Règlement, le Manuel infra-seuil et les dossiers types ?", ar: null },
  { fr: null, ar: "ما هي حالات عدم تطبيق مدونة الطلبية العمومية؟" },
];

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

function emptyConversation(): Conversation {
  return { id: uid(), title: "", messages: [], updatedAt: Date.now() };
}

function mostRecentId(list: Conversation[]): string | null {
  if (list.length === 0) return null;
  return [...list].sort((a, b) => b.updatedAt - a.updatedAt)[0].id;
}

export function ChatApp() {
  // Must start empty (not a lazy-loaded useState) so the client's first
  // render matches the server-rendered HTML — localStorage doesn't exist
  // on the server, so reading it in the initializer causes a hydration
  // mismatch. The load-on-mount effect below is the correct place for this:
  // it's syncing React state with an external store, exactly what effects
  // are for, not a case of the "derive state in an effect" anti-pattern.
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [targetLang, setTargetLang] = useState<"fr" | "ar">("fr");
  // Real state, not a ref: it must go through the same batched update/
  // re-render cycle as `conversations` so the save-effect below only ever
  // sees hydrated=true on a render where `conversations` also already
  // holds the loaded data — a ref mutated synchronously inside the effect
  // raced ahead of that and caused the save-effect to persist `[]` before
  // the load had actually landed, wiping real history on every reload.
  const [hydrated, setHydrated] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const stored = loadConversations();
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time hydration from localStorage, not derived render state
    setConversations(stored);
    setActiveId(mostRecentId(stored));
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (hydrated) saveConversations(conversations);
  }, [conversations, hydrated]);

  const active = conversations.find((c) => c.id === activeId) ?? null;
  const messages = useMemo(() => active?.messages ?? [], [active]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  function updateConversation(id: string, updater: (c: Conversation) => Conversation) {
    setConversations((prev) => prev.map((c) => (c.id === id ? updater(c) : c)));
  }

  function handleNewConversation() {
    const fresh = emptyConversation();
    setConversations((prev) => [fresh, ...prev]);
    setActiveId(fresh.id);
    setInput("");
  }

  function handleDeleteConversation(id: string) {
    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (activeId === id) setActiveId(null);
  }

  async function send(question: string) {
    if (!question.trim() || busy) return;
    setInput("");
    setBusy(true);

    let conversationId = activeId;
    if (!conversationId) {
      const fresh = emptyConversation();
      conversationId = fresh.id;
      setConversations((prev) => [fresh, ...prev]);
      setActiveId(fresh.id);
    }

    const userMsg: ChatMessage = { id: uid(), role: "user", content: question, lang: detectLang(question) };
    const pendingId = uid();

    updateConversation(conversationId, (c) => ({
      ...c,
      title: c.title || titleFromMessage(question),
      messages: [...c.messages, userMsg, { id: pendingId, role: "assistant", content: "", pending: true }],
      updatedAt: Date.now(),
    }));

    try {
      const res = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, top_k: 7, target_lang: targetLang }),
      });
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || "Erreur inconnue");
      }

      const answer = data as AskResponse;
      updateConversation(conversationId, (c) => ({
        ...c,
        messages: c.messages.map((m) =>
          m.id === pendingId
            ? { ...m, content: answer.answer, sources: answer.sources, lang: detectLang(answer.answer), pending: false }
            : m
        ),
        updatedAt: Date.now(),
      }));
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Erreur inconnue";
      updateConversation(conversationId, (c) => ({
        ...c,
        messages: c.messages.map((m) =>
          m.id === pendingId ? { ...m, pending: false, error: `Impossible d'obtenir une réponse : ${msg}` } : m
        ),
      }));
    } finally {
      setBusy(false);
    }
  }

  const isEmpty = messages.length === 0;

  return (
    <div className="flex h-dvh">
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={setActiveId}
        onNew={handleNewConversation}
        onDelete={handleDeleteConversation}
      />

      <div className="mx-auto flex h-dvh w-full max-w-3xl flex-col px-4">
        <header className="flex shrink-0 items-center justify-between gap-3 border-b border-line py-4">
          <div>
            <h1 className="font-display text-lg font-semibold text-ink">RégleMarchés AI</h1>
            <p className="text-[12.5px] text-ink-soft">Assistant juridique documentaire — marchés publics</p>
          </div>
          <div className="flex items-center gap-2">
            <LanguageToggle value={targetLang} onChange={setTargetLang} />
            <span className="hidden rounded-full border border-line bg-surface px-2.5 py-1 font-mono text-[11px] text-ink-soft sm:inline">
              5 documents
            </span>
          </div>
        </header>

        {isEmpty ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-6 text-center">
            <div>
              <h2 className="font-display text-2xl font-semibold text-ink">Posez votre question</h2>
              <p className="mx-auto mt-2 max-w-sm text-[13.5px] text-ink-soft">
                Réponses sourcées à partir du Règlement des marchés de la BCM, du Code de la Commande Publique (FR/AR)
                et du règlement de passation des marchés de la Banque Mondiale.
              </p>
            </div>
            <div className="flex max-w-lg flex-wrap justify-center gap-2">
              {EXAMPLE_PROMPTS.map((p, i) => {
                const text = (p.fr ?? p.ar) as string;
                const dir = p.ar ? "rtl" : "ltr";
                return (
                  <button
                    key={i}
                    dir={dir}
                    onClick={() => send(text)}
                    className="rounded-full border border-line bg-surface px-3.5 py-1.5 text-[13px] text-ink-soft transition-colors hover:border-accent hover:text-ink"
                  >
                    {text}
                  </button>
                );
              })}
            </div>
          </div>
        ) : (
          <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto py-6">
            {messages.map((m) => (
              <MessageBubble key={m.id} message={m} />
            ))}
          </div>
        )}

        <div className="shrink-0 pb-5 pt-3">
          <Composer value={input} onChange={setInput} onSubmit={() => send(input)} disabled={busy} />
          <p className="mt-2 text-center text-[11px] text-ink-faint">
            Les réponses citent leurs sources mais peuvent contenir des erreurs — vérifiez les articles cités.
          </p>
        </div>
      </div>
    </div>
  );
}
