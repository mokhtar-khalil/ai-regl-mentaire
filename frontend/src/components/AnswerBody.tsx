import React from "react";

/**
 * Minimal renderer for the backend's answer format: **Section** headings,
 * paragraphs, "- " bullet lists, and [n] / [n][m] citation markers. Not a
 * general markdown engine — the system prompt controls the output shape
 * tightly enough that this is simpler and lighter than pulling in a full
 * markdown library for a handful of patterns.
 */

const CITATION_RE = /\[(\d+)\]/g;
const BOLD_RE = /\*\*(.+?)\*\*/g;

function renderInline(text: string, onCiteClick: (n: number) => void, keyPrefix: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = [];
  let lastIndex = 0;
  let counter = 0;

  // Interleave bold-splitting and citation-splitting by scanning once for
  // whichever pattern matches first at each position.
  const combined = new RegExp(`${BOLD_RE.source}|${CITATION_RE.source}`, "g");
  let match: RegExpExecArray | null;
  while ((match = combined.exec(text))) {
    if (match.index > lastIndex) {
      nodes.push(text.slice(lastIndex, match.index));
    }
    if (match[1] !== undefined) {
      nodes.push(
        <strong key={`${keyPrefix}-b${counter++}`} className="font-semibold text-ink">
          {match[1]}
        </strong>
      );
    } else if (match[2] !== undefined) {
      const n = parseInt(match[2], 10);
      nodes.push(
        <button
          key={`${keyPrefix}-c${counter++}`}
          type="button"
          onClick={() => onCiteClick(n)}
          className="mx-0.5 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-accent-soft px-1 font-mono text-[10px] font-medium text-accent-ink align-super leading-none hover:bg-accent hover:text-white transition-colors"
        >
          {n}
        </button>
      );
    }
    lastIndex = combined.lastIndex;
  }
  if (lastIndex < text.length) nodes.push(text.slice(lastIndex));
  return nodes;
}

export function AnswerBody({ text, onCiteClick }: { text: string; onCiteClick: (n: number) => void }) {
  const blocks = text.trim().split(/\n\s*\n/);

  return (
    <div className="chat-prose">
      {blocks.map((block, i) => {
        const trimmed = block.trim();
        const headingMatch = trimmed.match(/^\*\*(.+?):?\*\*$/);
        if (headingMatch && trimmed.length < 80) {
          return (
            <p
              key={i}
              className="mb-1.5 mt-3 font-mono text-[11px] font-semibold uppercase tracking-wide text-accent first:mt-0"
            >
              {headingMatch[1]}
            </p>
          );
        }

        const lines = trimmed.split("\n").map((l) => l.trim());
        const isList = lines.every((l) => /^([-*•]|\d+\.)\s+/.test(l));
        if (isList) {
          const ordered = /^\d+\./.test(lines[0]);
          const items = lines.map((l) => l.replace(/^([-*•]|\d+\.)\s+/, ""));
          const ListTag = ordered ? "ol" : "ul";
          return (
            <ListTag key={i} className={ordered ? "list-decimal" : "list-disc"}>
              {items.map((item, j) => (
                <li key={j}>{renderInline(item, onCiteClick, `${i}-${j}`)}</li>
              ))}
            </ListTag>
          );
        }

        return <p key={i}>{renderInline(trimmed, onCiteClick, `${i}`)}</p>;
      })}
    </div>
  );
}
