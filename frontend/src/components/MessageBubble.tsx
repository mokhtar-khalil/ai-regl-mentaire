"use client";

import { useState } from "react";
import { ChatMessage } from "@/lib/types";
import { AnswerBody } from "./AnswerBody";
import { SourceList } from "./SourceList";

function ThinkingIndicator() {
  return (
    <div className="flex items-center gap-1.5 py-1">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 rounded-full bg-ink-faint"
          style={{
            animation: "pulse-dot 1.1s ease-in-out infinite",
            animationDelay: `${i * 0.15}s`,
          }}
        />
      ))}
      <style>{`
        @keyframes pulse-dot {
          0%, 60%, 100% { opacity: 0.25; transform: scale(0.85); }
          30% { opacity: 1; transform: scale(1); }
        }
      `}</style>
    </div>
  );
}

export function MessageBubble({ message }: { message: ChatMessage }) {
  const [activeSource, setActiveSource] = useState<number | null>(null);
  const isUser = message.role === "user";
  const lang = message.lang ?? "fr";
  const dir = lang === "ar" ? "rtl" : "ltr";

  const handleCiteClick = (n: number) => {
    setActiveSource(n);
    document.getElementById(`source-${n}`)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    window.setTimeout(() => setActiveSource((cur) => (cur === n ? null : cur)), 1800);
  };

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div
          dir={dir}
          className="max-w-[85%] rounded-2xl rounded-br-sm bg-surface-user px-4 py-2.5 text-[14.5px] text-ink"
        >
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div
        dir={dir}
        className={`max-w-[94%] rounded-2xl rounded-bl-sm border px-5 py-4 text-[14.5px] leading-relaxed sm:max-w-[88%] ${
          message.error ? "border-danger-soft bg-danger-soft text-danger" : "border-line bg-surface text-ink"
        }`}
      >
        {message.pending && !message.content ? (
          <ThinkingIndicator />
        ) : message.error ? (
          <p>{message.error}</p>
        ) : (
          <>
            <AnswerBody text={message.content} onCiteClick={handleCiteClick} />
            {message.pending && (
              <span className="mt-2 inline-block h-4 w-0.5 animate-pulse bg-accent" aria-label="Réponse en cours" />
            )}
            {message.sources && message.sources.length > 0 && (
              <SourceList sources={message.sources} lang={lang} activeIndex={activeSource} />
            )}
          </>
        )}
      </div>
    </div>
  );
}
