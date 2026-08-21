import { NextRequest, NextResponse } from "next/server";

// Server-side proxy to the FastAPI RAG backend — keeps the backend URL out
// of client bundles and sidesteps CORS entirely.
const API_URL = process.env.RAG_API_URL || "http://127.0.0.1:8000";

export async function POST(req: NextRequest) {
  let body: { question?: string; top_k?: number; target_lang?: "fr" | "ar" };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  if (!body.question || !body.question.trim()) {
    return NextResponse.json({ error: "question is required" }, { status: 400 });
  }

  try {
    const upstream = await fetch(`${API_URL}/ask/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: body.question, top_k: body.top_k ?? 7, target_lang: body.target_lang ?? null }),
      signal: AbortSignal.any([req.signal, AbortSignal.timeout(120_000)]),
    });

    if (!upstream.ok) {
      const text = await upstream.text();
      return NextResponse.json(
        { error: `Backend error (${upstream.status})`, detail: text.slice(0, 500) },
        { status: 502 }
      );
    }

    if (!upstream.body) {
      return NextResponse.json({ error: "Le backend n'a retourné aucun flux" }, { status: 502 });
    }

    return new Response(upstream.body, {
      status: upstream.status,
      headers: {
        "Content-Type": upstream.headers.get("Content-Type") || "application/x-ndjson; charset=utf-8",
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",
      },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ error: `Impossible de joindre le backend : ${message}` }, { status: 502 });
  }
}
