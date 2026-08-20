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

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  lang?: "fr" | "ar";
  pending?: boolean;
  error?: string;
}
