"use client";

import { useEffect, useRef, useState } from "react";
import { ChatMessage, AskResponse } from "@/lib/types";
import { detectLang } from "@/lib/lang";
import { MessageBubble } from "./MessageBubble";
import { Composer } from "./Composer";

const EXAMPLE_PROMPTS = [
  { fr: "Quels sont les seuils de passation des marchés de la BCM ?", ar: null },
  { fr: "Quelle est la hiérarchie entre le Règlement, le Manuel infra-seuil et les dossiers types ?", ar: null },
  { fr: null, ar: "ما هي حالات عدم تطبيق مدونة الطلبية العمومية؟" },
];

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

export function ChatApp() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function send(question: string) {
    if (!question.trim() || busy) return;
    setInput("");
    setBusy(true);

    const userMsg: ChatMessage = { id: uid(), role: "user", content: question, lang: detectLang(question) };
    const pendingId = uid();
    setMessages((prev) => [...prev, userMsg, { id: pendingId, role: "assistant", content: "", pending: true }]);

    try {
      const res = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, top_k: 10 }),
      });
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || "Erreur inconnue");
      }

      const answer = data as AskResponse;
      setMessages((prev) =>
        prev.map((m) =>
          m.id === pendingId
            ? { ...m, content: answer.answer, sources: answer.sources, lang: detectLang(answer.answer), pending: false }
            : m
        )
      );
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Erreur inconnue";
      setMessages((prev) =>
        prev.map((m) =>
          m.id === pendingId ? { ...m, pending: false, error: `Impossible d'obtenir une réponse : ${msg}` } : m
        )
      );
    } finally {
      setBusy(false);
    }
  }

  const isEmpty = messages.length === 0;

  return (
    <div className="mx-auto flex h-dvh max-w-3xl flex-col px-4">
      <header className="flex shrink-0 items-center justify-between border-b border-line py-4">
        <div>
          <h1 className="font-display text-lg font-semibold text-ink">RAG Réglementaire</h1>
          <p className="text-[12.5px] text-ink-soft">Assistant juridique documentaire — marchés publics</p>
        </div>
        <span className="rounded-full border border-line bg-surface px-2.5 py-1 font-mono text-[11px] text-ink-soft">
          5 documents · FR / AR
        </span>
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
  );
}
