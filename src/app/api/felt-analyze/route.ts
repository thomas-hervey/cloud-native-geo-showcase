import Anthropic from "@anthropic-ai/sdk";
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { checkRateLimit } from "@/lib/rate-limit";

const BodySchema = z.object({
  prompt: z.string().min(1),
  context: z.string().optional(),
  // BYOK: required on any deployed (production) instance. This route is public
  // and unauthenticated, so the server key is only used outside production
  // (local tutorial use); see resolveApiKey().
  apiKey: z.string().optional(),
});

// Felt extensions run in a sandboxed iframe whose origin is reported as "null".
// We must explicitly allow it so the preflight and actual request both succeed.
const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "null",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

/**
 * Resolve the Anthropic key for a request. A caller-supplied key always wins.
 * The server key (ANTHROPIC_API_KEY from .env.local) is a fallback for local
 * tutorial use only: every Vercel deployment runs with NODE_ENV=production, so a
 * deployed instance can never be used as an open proxy to the owner's key.
 */
function resolveApiKey(bodyKey: string | undefined): string | undefined {
  if (bodyKey) return bodyKey;
  if (process.env.NODE_ENV !== "production") return process.env.ANTHROPIC_API_KEY || undefined;
  return undefined;
}

export async function OPTIONS() {
  return new NextResponse(null, { status: 204, headers: CORS_HEADERS });
}

export async function POST(req: NextRequest) {
  const ip = req.headers.get("x-forwarded-for") ?? "127.0.0.1";
  if (!checkRateLimit(ip)) {
    return NextResponse.json(
      { error: "Too many requests. Please try again later." },
      { status: 429, headers: CORS_HEADERS }
    );
  }

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400, headers: CORS_HEADERS });
  }

  const parsed = BodySchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json(
      { error: parsed.error.flatten().fieldErrors },
      { status: 400, headers: CORS_HEADERS }
    );
  }

  const { prompt, context } = parsed.data;
  const apiKey = resolveApiKey(parsed.data.apiKey);

  if (!apiKey) {
    return NextResponse.json(
      {
        error:
          process.env.NODE_ENV === "production"
            ? "Missing API key. Send your own Anthropic key as \"apiKey\" in the request body."
            : "Missing API key. Set ANTHROPIC_API_KEY in .env.local or send your own key as \"apiKey\" in the request body.",
      },
      { status: 401, headers: CORS_HEADERS }
    );
  }

  const client = new Anthropic({ apiKey });

  try {
    // Using claude-haiku for fast, low-cost responses in the tutorial proxy
    const message = await client.messages.create({
      model: "claude-haiku-4-5-20251001",
      max_tokens: 1024,
      messages: [
        {
          role: "user",
          content: context
            ? `Context:\n${context}\n\nQuestion: ${prompt}`
            : prompt,
        },
      ],
    });

    const text = message.content
      .filter((block) => block.type === "text")
      .map((block) => block.text)
      .join("");

    return NextResponse.json({ response: text }, { headers: CORS_HEADERS });
  } catch (err) {
    console.error("felt-analyze LLM error:", err);
    return NextResponse.json(
      { error: "LLM request failed" },
      { status: 502, headers: CORS_HEADERS }
    );
  }
}
