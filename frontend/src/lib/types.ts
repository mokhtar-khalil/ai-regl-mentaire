export interface Source {
  index: number;
  document: string;
  document_label: string;
  chapter?: string | null;
  article_num?: string | null;
  article_title?: string | null;
  page_start?: number | null;
  page_end?: number | null;
  rrf_score?: number | null;
}

export interface AskResponse {
  answer: string;
  sources: Source[];
}

export type AskStreamEvent =
  | { type: "status"; request_id: string; stage: string }
  | { type: "delta"; text: string }
  | { type: "done"; answer: string; sources: Source[]; timings: Record<string, number | null> }
  | { type: "error"; error: string };

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  lang?: "fr" | "ar";
  pending?: boolean;
  error?: string;
}

export interface Conversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  updatedAt: number;
}
