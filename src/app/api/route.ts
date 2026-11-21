/**
 * GET /api
 *
 * Machine-readable manifest of all API routes — their auth requirements,
 * purpose, and accepted methods. Useful for agents, developers, and
 * onboarding docs.
 *
 * Auth: public (no session required)
 */

import { NextResponse } from "next/server";

const ROUTES = [
  // ── Public routes (no auth required) ────────────────────────────────────
  {
    path: "/api/felt-analyze",
    methods: ["POST"],
    auth: "none",
    note: "Claude proxy for the Toxic Legacy Felt Extension. Called from a sandboxed iframe (origin: null). In production requires a BYOK Anthropic key as apiKey in the request body (401 otherwise); the server ANTHROPIC_API_KEY fallback applies only when NODE_ENV is not production (local dev). Rate limited per IP.",
  },
  {
    path: "/api/epa-facilities",
    methods: ["GET"],
    auth: "none",
    note: "Serves TRI facilities from a static Bay Area JSON snapshot (not a live EPA proxy). Returns facilities near a lat/lon. Params: lat, lon, radiusMiles, type (TRI|NPL). Called from Felt Extension.",
  },
  {
    path: "/api/readme",
    methods: ["GET"],
    auth: "none",
    note: "Returns the README.md for a tutorial exercise. Query param: ?module=<slug>",
  },
  {
    path: "/api",
    methods: ["GET"],
    auth: "none",
    note: "This manifest.",
  },

  {
    path: "/api/scout/replay",
    methods: ["GET"],
    auth: "none",
    note: "Recorded Scout run for the public demo. Params: id (must match an entry in src/content/scout-replays/index.json). No LLM call.",
  },

  // ── Auth-required routes (Supabase session) ──────────────────────────────
  {
    path: "/api/scout/query",
    methods: ["POST"],
    auth: "supabase-session",
    note: "Natural-language spatial query against the Scout DuckDB dataset. Live LLM only for super-admin when LIVE_LLM_ENABLED=true; otherwise 403 live_llm_disabled.",
  },
  {
    path: "/api/scout/generative-query",
    methods: ["POST"],
    auth: "supabase-session",
    note: "Generative (RAG-style) spatial query with LLM-synthesised narrative. Live LLM only for super-admin when LIVE_LLM_ENABLED=true; otherwise 403 live_llm_disabled.",
  },
  {
    path: "/api/scout/rag-query",
    methods: ["POST"],
    auth: "supabase-session",
    note: "RAG query variant using embedded document context. Live LLM only for super-admin when LIVE_LLM_ENABLED=true; otherwise 403 live_llm_disabled.",
  },
  {
    path: "/api/scout/agent-query",
    methods: ["POST"],
    auth: "supabase-session",
    note: "Agentic query that plans multi-step spatial reasoning. Live LLM only for super-admin when LIVE_LLM_ENABLED=true; otherwise 403 live_llm_disabled.",
  },
] as const;

export async function GET() {
  return NextResponse.json({
    description:
      "Cloud-Native Geo Tutorial API. Routes marked auth:none are publicly reachable. " +
      "All other routes require a valid Supabase session cookie.",
    routes: ROUTES,
  });
}
