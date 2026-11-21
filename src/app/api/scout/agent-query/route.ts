/**
 * Scout Module 27 — Agent API Route
 * ===================================
 * POST /api/scout/agent-query
 *
 * Runs a multi-turn agentic loop server-side using Anthropic tool use.
 * The agent has access to four tools:
 *   - search_datasets: semantic search over retrieval_index.json (Module 26)
 *   - execute_sql:     sends SQL to the browser bridge (DuckDB-Wasm executes it)
 *   - get_map_extent:  reads the map viewport bbox from the request body
 *   - ask_clarification: returns a clarification request to the UI
 *
 * Request body:
 *   {
 *     query: string,          // user's natural language question
 *     bbox?: {                // current map viewport (from MapLibre getBounds())
 *       west: number, south: number, east: number, north: number
 *     },
 *     sql_result?: {          // populated on round 2+ when browser sends DuckDB result back
 *       sql: string,
 *       row_count: number,
 *       columns: string[],
 *       sample_rows: Record<string, unknown>[]
 *     }
 *   }
 *
 * Response:
 *   {
 *     sql: string,            // the final SQL for DuckDB-Wasm to execute
 *     reasoning_trace: ToolCall[],
 *     provider: string,
 *     usage: { input_tokens, output_tokens, total_tokens }
 *   }
 *   OR
 *   {
 *     clarification_needed: string  // agent asked the user a question
 *   }
 *   OR
 *   {
 *     sql_execution_needed: string  // SQL generated but not yet executed (browser must execute)
 *   }
 */

import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import Anthropic from "@anthropic-ai/sdk";
import { buildDatasetSystemPromptSection } from "@/lib/scout-datasets-server";
import { validateSql, enforceLimitClause } from "@/lib/scout-guards";
import { checkRateLimit } from "@/lib/rate-limit";
import { getLlmAccess } from '@/lib/llm-access';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface BoundingBox {
  west: number;
  south: number;
  east: number;
  north: number;
}

interface SqlResult {
  sql: string;
  row_count: number;
  columns: string[];
  sample_rows: Record<string, unknown>[];
  error?: string;
}

export interface ToolCall {
  step: number;
  tool: string;
  input: Record<string, unknown>;
  output: string;
  elapsed_ms: number;
}

interface IndexDoc {
  id: string;
  document: string;
  metadata: Record<string, string | number | boolean | null>;
}

// ---------------------------------------------------------------------------
// Pipeline constants (same as RAG route)
// ---------------------------------------------------------------------------

import { PIPELINE } from "@/lib/scout-pipeline";

const MAX_AGENT_TURNS = 6; // safety cap on tool call rounds

// ---------------------------------------------------------------------------
// Tool definitions (Anthropic format)
// ---------------------------------------------------------------------------

const TOOLS: Anthropic.Tool[] = [
  {
    name: "search_datasets",
    description:
      "Search the Scout schema index for datasets relevant to a natural language query. " +
      "Returns top matching schemas to use when writing SQL. " +
      "Call this before writing any SQL so you know the correct table names and columns.",
    input_schema: {
      type: "object" as const,
      properties: {
        query: {
          type: "string",
          description: "Natural language description of the data you need",
        },
      },
      required: ["query"],
    },
  },
  {
    name: "execute_sql",
    description:
      "Execute a DuckDB SQL SELECT against the Scout geospatial database. " +
      "Start every query with 'LOAD spatial;'. " +
      "Returns {row_count, columns, sample_rows} on success, or {error} on failure. " +
      "If the query fails, read the error, call search_datasets to check the schema, then retry.",
    input_schema: {
      type: "object" as const,
      properties: {
        sql: {
          type: "string",
          description:
            "Complete DuckDB SQL SELECT. First line must be 'LOAD spatial;'",
        },
      },
      required: ["sql"],
    },
  },
  {
    name: "get_map_extent",
    description:
      "Returns the current Scout map viewport bounding box as {west, south, east, north}. " +
      "Use this to scope queries to what the user is currently viewing. " +
      "Call this for queries that don't specify a location.",
    input_schema: {
      type: "object" as const,
      properties: {},
      required: [],
    },
  },
  {
    name: "ask_clarification",
    description:
      "Ask the user a clarifying question when a query is genuinely ambiguous. " +
      "Only use when ambiguity would materially change the SQL. " +
      "Prefer a reasonable assumption over asking.",
    input_schema: {
      type: "object" as const,
      properties: {
        question: {
          type: "string",
          description: "Clarifying question in plain English",
        },
      },
      required: ["question"],
    },
  },
];

// ---------------------------------------------------------------------------
// Tool handlers
// ---------------------------------------------------------------------------

function loadIndex(): IndexDoc[] {
  const candidates = [
    path.join(process.cwd(), "public", "data", "retrieval_index.json"),
    path.join(
      process.cwd(),
      "src",
      "exercises",
      "26-vector-rag",
      "output",
      "retrieval_index.json"
    ),
  ];
  for (const p of candidates) {
    if (fs.existsSync(p)) {
      return (JSON.parse(fs.readFileSync(p, "utf-8")) as { documents: IndexDoc[] }).documents;
    }
  }
  throw new Error(
    "retrieval_index.json not found. Run src/exercises/26-vector-rag/03_onboard_buildings.py first."
  );
}

function toolSearchDatasets(query: string): string {
  let docs: IndexDoc[];
  try {
    docs = loadIndex();
  } catch (e) {
    return JSON.stringify({ error: String(e) });
  }

  const queryTokens = new Set(query.toLowerCase().split(/\W+/).filter(Boolean));
  const scored = docs.map((doc) => {
    const tokens = doc.document.toLowerCase().split(/\W+/).filter(Boolean);
    let hits = 0;
    for (const t of tokens) if (queryTokens.has(t)) hits++;
    return { doc, score: queryTokens.size > 0 ? hits / queryTokens.size : 0 };
  });

  const top = scored
    .sort((a, b) => b.score - a.score)
    .slice(0, PIPELINE.TOP_K)
    .filter((x) => x.score > PIPELINE.SIM_THRESHOLD)
    .map(({ doc, score }) => ({
      dataset_id: String(doc.metadata.dataset_id ?? "?"),
      chunk_type: String(doc.metadata.chunk_type ?? "?"),
      similarity: Math.round(score * 1000) / 1000,
      text: doc.document.slice(0, 400),
    }));

  return JSON.stringify(top.length > 0 ? top : [{ note: "No datasets matched above threshold." }]);
}

function toolGetMapExtent(bbox?: BoundingBox): string {
  return JSON.stringify(
    bbox ?? {
      west: -122.5152,
      south: 37.7079,
      east: -122.3591,
      north: 37.8324,
      note: "Default SF bbox — map viewport not provided in request.",
    }
  );
}

// execute_sql is handled specially — the server can't run DuckDB-Wasm.
// Instead, we return a sentinel that the client recognizes and executes.
// The client then calls this route again with sql_result populated.
function toolExecuteSqlSentinel(sql: string): { sentinel: true; sql: string } {
  return { sentinel: true, sql };
}

// ---------------------------------------------------------------------------
// System prompt
// ---------------------------------------------------------------------------

function buildSystemPrompt(): string {
  return `You are Scout, a geospatial AI assistant that helps users explore San Francisco data.

You have access to tools that let you:
1. Search the dataset schema index to find the right tables and columns
2. Execute SQL queries against real geospatial data in DuckDB
3. Get the user's current map viewport to scope spatial queries
4. Ask the user for clarification when needed

## Guiding principles
- Always call search_datasets BEFORE writing SQL so you know the schema
- Be efficient — complete the task in 3 or fewer tool calls
- After getting the schema you need, return a single final SQL statement

${buildDatasetSystemPromptSection()}

## CRITICAL DuckDB spatial rules — read carefully
1. **NEVER use ST_GeomFromWKB()** — the geometry columns in Overture parquet are already native GEOMETRY type. Wrapping them in ST_GeomFromWKB() causes a type error.
2. For proximity queries between lat/lon points, use the Haversine approximation or degrees distance — NO spatial joins needed:
   \`\`\`sql
   LOAD spatial;
   SELECT id, name, category, lat, lon
   FROM places
   WHERE category IN ('coffee_shop')
     AND ABS(lat - 37.7596) < 0.01 AND ABS(lon - (-122.4269)) < 0.01
   LIMIT 200;
   \`\`\`
3. For ST_DWithin, only use it with ST_Point() constructed from lat/lon columns — do NOT reference a geometry column directly:
   \`\`\`sql
   LOAD spatial;
   SELECT id, name, category, lat, lon
   FROM places
   WHERE category IN ('coffee_shop')
     AND ST_DWithin(ST_Point(lon, lat), ST_Point(-122.4269, 37.7596), 0.005)
   LIMIT 200;
   \`\`\`
4. Do NOT use SELECT *, never include geometry columns in SELECT
5. Always start with: LOAD spatial;
6. LIMIT 200 rows unless otherwise asked
7. Never use INSERT, UPDATE, DELETE, DROP, CREATE

## SQL format
Return ONLY the SQL statement, nothing else. No explanation. No markdown code fences.

Reason step-by-step, but keep your reasoning brief.`;
}


// ---------------------------------------------------------------------------
// Agent loop
// ---------------------------------------------------------------------------

interface AgentResult {
  sql: string | null;
  reasoning_trace: ToolCall[];
  clarification_needed: string | null;
  provider: string;
  usage: { input_tokens: number; output_tokens: number; total_tokens: number };
}

async function runAgentLoop(
  query: string,
  bbox: BoundingBox | undefined,
  sqlResult: SqlResult | undefined
): Promise<AgentResult> {
  const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

  const messages: Anthropic.MessageParam[] = [{ role: "user", content: query }];

  // If a previous sql_result is provided (round 2+), inject it
  if (sqlResult) {
    messages.push({
      role: "user",
      content: sqlResult.error
        ? `The SQL returned an error: ${sqlResult.error}\nSQL was: ${sqlResult.sql}`
        : `The SQL executed successfully. Results: ${JSON.stringify(sqlResult)}`,
    });
  }

  const trace: ToolCall[] = [];
  let totalInputTokens = 0;
  let totalOutputTokens = 0;
  let finalSql: string | null = null;
  let clarification: string | null = null;

  for (let turn = 0; turn < MAX_AGENT_TURNS; turn++) {
    const response = await client.messages.create({
      model: PIPELINE.CLAUDE_MODEL,
      max_tokens: PIPELINE.MAX_TOKENS * 2, // agents need more room to reason
      system: buildSystemPrompt(),
      tools: TOOLS,
      messages,
    });

    totalInputTokens += response.usage.input_tokens;
    totalOutputTokens += response.usage.output_tokens;

    // Check stop reason
    if (response.stop_reason === "end_turn") {
      // Extract SQL from the text response
      const textBlock = response.content.find((b) => b.type === "text");
      if (textBlock && textBlock.type === "text") {
        const sqlMatch = textBlock.text.match(/LOAD spatial;[\s\S]+/i);
        const extracted = sqlMatch ? sqlMatch[0].trim() : textBlock.text.trim();
        const validation = validateSql(extracted);
        if (validation.valid) {
          finalSql = enforceLimitClause(extracted);
        }
      }
      break;
    }

    if (response.stop_reason !== "tool_use") break;

    // Append assistant turn
    messages.push({ role: "assistant", content: response.content });

    // Process each tool_use block
    const toolResults: Anthropic.ToolResultBlockParam[] = [];

    for (const block of response.content) {
      if (block.type !== "tool_use") continue;

      const stepStart = Date.now();
      const input = block.input as Record<string, unknown>;
      let output: string;

      if (block.name === "execute_sql") {
        // Capture the SQL and stop. The browser will execute it.
        // Only the FIRST execute_sql call counts — subsequent calls are
        // exploratory diagnostics that would overwrite the correct query.
        const sentinel = toolExecuteSqlSentinel(input.sql as string);
        finalSql = sentinel.sql;
        output = JSON.stringify({ note: "SQL will be executed in browser DuckDB-Wasm." });
        trace.push({
          step: trace.length + 1,
          tool: block.name,
          input,
          output: output.slice(0, 300),
          elapsed_ms: Date.now() - stepStart,
        });
        // Guard: validate and enforce limits before handing off to the browser
        if (finalSql) {
          const validation = validateSql(finalSql);
          if (!validation.valid) {
            output = JSON.stringify({ error: `SQL rejected: ${validation.reason}` });
            finalSql = null;
          } else {
            finalSql = enforceLimitClause(finalSql);
          }
        }

        // Don't continue the loop — this is the terminal action.
        // totalInputTokens/totalOutputTokens were already incremented at the top
        // of this loop iteration (lines above the tool-use branch), so use them
        // directly — adding response.usage again would double-count this turn.
        return {
          sql: finalSql,
          reasoning_trace: trace,
          clarification_needed: null,
          provider: `claude-agent (${PIPELINE.CLAUDE_MODEL})`,
          usage: {
            input_tokens: totalInputTokens,
            output_tokens: totalOutputTokens,
            total_tokens: totalInputTokens + totalOutputTokens,
          },
        };
      }

      switch (block.name) {
        case "search_datasets":
          output = toolSearchDatasets(input.query as string);
          break;
        case "get_map_extent":
          output = toolGetMapExtent(bbox);
          break;
        case "ask_clarification":
          clarification = input.question as string;
          output = JSON.stringify({ status: "clarification_requested" });
          break;
        default:
          output = JSON.stringify({ error: `Unknown tool: ${block.name}` });
      }

      trace.push({
        step: trace.length + 1,
        tool: block.name,
        input,
        output: output.slice(0, 500),
        elapsed_ms: Date.now() - stepStart,
      });

      toolResults.push({ type: "tool_result", tool_use_id: block.id, content: output });

      // If agent asked for clarification, stop the loop
      if (clarification) break;
    }

    if (clarification) break;

    // Append tool results and continue the loop
    messages.push({ role: "user", content: toolResults });
  }

  return {
    sql: finalSql,
    reasoning_trace: trace,
    clarification_needed: clarification,
    provider: `claude-agent (${PIPELINE.CLAUDE_MODEL})`,
    usage: {
      input_tokens: totalInputTokens,
      output_tokens: totalOutputTokens,
      total_tokens: totalInputTokens + totalOutputTokens,
    },
  };
}

// ---------------------------------------------------------------------------
// POST handler
// ---------------------------------------------------------------------------

export async function POST(request: NextRequest) {
  // 0. Rate limit check
  const ip = request.headers.get("x-forwarded-for") ?? "127.0.0.1";
  if (!checkRateLimit(ip)) {
    return NextResponse.json(
      { error: "Too many requests. Please try again later." },
      { status: 429 }
    );
  }

  // LLM spend gate: must run before any API key is read or client constructed.
  const llmAccess = await getLlmAccess();
  if (llmAccess.mode !== 'live') {
    return NextResponse.json({ error: 'live_llm_disabled', mode: 'replay' }, { status: 403 });
  }

  let query: string;
  let bbox: BoundingBox | undefined;
  let sqlResult: SqlResult | undefined;

  try {
    const body = await request.json();
    query = body?.query?.trim();
    bbox = body?.bbox;
    sqlResult = body?.sql_result;

    if (!query) {
      return NextResponse.json({ error: "Missing required field: query" }, { status: 400 });
    }
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  if (!process.env.ANTHROPIC_API_KEY) {
    return NextResponse.json(
      { error: 'Missing API key', details: 'Set ANTHROPIC_API_KEY in your .env.local file.' },
      { status: 503 }
    );
  }

  try {
    const result = await runAgentLoop(query, bbox, sqlResult);

    if (result.clarification_needed) {
      return NextResponse.json({ clarification_needed: result.clarification_needed });
    }

    return NextResponse.json({
      sql: result.sql,
      reasoning_trace: result.reasoning_trace,
      provider: result.provider,
      usage: result.usage,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: "Agent loop failed", details: message }, { status: 502 });
  }
}
