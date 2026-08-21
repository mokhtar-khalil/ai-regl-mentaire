import React from "react";

const CITATION_RE = /\[(\d+)\]/g;
const BOLD_RE = /\*\*(.+?)\*\*/g;

type AnswerBlock =
  | { type: "heading"; text: string }
  | { type: "paragraph"; text: string }
  | { type: "list"; ordered: boolean; items: string[] };

function renderInline(text: string, onCiteClick: (n: number) => void, keyPrefix: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = [];
  let lastIndex = 0;
  let counter = 0;
  const combined = new RegExp(`${BOLD_RE.source}|${CITATION_RE.source}`, "g");
  let match: RegExpExecArray | null;

  while ((match = combined.exec(text))) {
    if (match.index > lastIndex) nodes.push(text.slice(lastIndex, match.index));

    if (match[1] !== undefined) {
      nodes.push(
        <strong key={`${keyPrefix}-b${counter++}`} className="font-semibold text-ink">
          {match[1]}
        </strong>
      );
    } else if (match[2] !== undefined) {
      const n = Number.parseInt(match[2], 10);
      nodes.push(
        <button
          key={`${keyPrefix}-c${counter++}`}
          type="button"
          onClick={() => onCiteClick(n)}
          aria-label={`Voir la référence ${n}`}
          className="mx-0.5 inline-flex min-w-5 items-center justify-center rounded bg-accent-soft px-1 font-mono text-[11px] font-semibold leading-5 text-accent transition-colors hover:bg-accent hover:text-white"
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

function parseAnswer(text: string): AnswerBlock[] {
  const blocks: AnswerBlock[] = [];
  let paragraph: string[] = [];
  let list: { ordered: boolean; items: string[] } | null = null;

  const flushParagraph = () => {
    if (paragraph.length) blocks.push({ type: "paragraph", text: paragraph.join(" ") });
    paragraph = [];
  };
  const flushList = () => {
    if (list?.items.length) blocks.push({ type: "list", ...list });
    list = null;
  };

  const consumeContent = (content: string) => {
    const listMatch = content.match(/^([-*•]|\d+\.)\s+(.+)$/);
    if (listMatch) {
      flushParagraph();
      const ordered = /^\d+\.$/.test(listMatch[1]);
      if (list && list.ordered !== ordered) flushList();
      if (!list) list = { ordered, items: [] };
      list.items.push(listMatch[2]);
      return;
    }

    flushList();
    paragraph.push(content);
  };

  for (const rawLine of text.trim().split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line) {
      flushParagraph();
      flushList();
      continue;
    }

    const markdownHeading = line.match(/^#{1,3}\s+(.+)$/);
    const boldHeading = line.match(/^\*\*([^*\n]{1,80}?)\*\*(?:\s+(.+))?$/);
    if (markdownHeading || boldHeading) {
      flushParagraph();
      flushList();
      blocks.push({ type: "heading", text: markdownHeading?.[1] ?? boldHeading?.[1] ?? "" });
      const remainder = boldHeading?.[2];
      if (remainder) consumeContent(remainder);
      continue;
    }

    consumeContent(line);
  }

  flushParagraph();
  flushList();
  return blocks;
}

export function AnswerBody({ text, onCiteClick }: { text: string; onCiteClick: (n: number) => void }) {
  const blocks = parseAnswer(text);

  return (
    <div className="chat-prose">
      {blocks.map((block, i) => {
        if (block.type === "heading") {
          return (
            <h3
              key={i}
              className="mb-2 mt-5 border-b border-line pb-1.5 font-display text-[17px] font-semibold text-accent-ink first:mt-0"
            >
              {block.text}
            </h3>
          );
        }

        if (block.type === "list") {
          const ListTag = block.ordered ? "ol" : "ul";
          return (
            <ListTag key={i} className={block.ordered ? "list-decimal" : "list-disc"}>
              {block.items.map((item, j) => (
                <li key={j}>{renderInline(item, onCiteClick, `${i}-${j}`)}</li>
              ))}
            </ListTag>
          );
        }

        return <p key={i}>{renderInline(block.text, onCiteClick, `${i}`)}</p>;
      })}
    </div>
  );
}
