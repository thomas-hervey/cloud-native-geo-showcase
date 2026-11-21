/**
 * Scout Exercise 1: Tool Definitions & Handler Stubs
 * ===============================================================
 * Run this standalone script to understand the Anthropic tool-calling
 * protocol before wiring it into a Next.js route.
 *
 * This exercise does THREE things:
 *
 *  1. Defines the four Anthropic tool schemas for the Scout agent
 *  2. Implements the handler functions that back each tool
 *  3. Runs a DRY RUN showing the raw JSON message flow for a sample query
 *     (no real LLM call — we mock the assistant turn to avoid API costs)
 *
 * Key concept: tool calling is a two-part message exchange.
 *   Turn 1: You send messages + tools → LLM returns a tool_use block
 *   Turn 2: You execute the tool, append the tool_result → LLM returns text
 *
 * Reading order:
 *   1. TOOL_DEFINITIONS — the JSON schemas the LLM sees
 *   2. Tool handler functions — the code that executes the tool
 *   3. simulatedAgentLoop() — shows what the message array looks like at each step
 *
 * Run:
 *   cd src/exercises/agentic
 *   npx ts-node 01_tool_definitions.ts
 *   # or: npx tsx 01_tool_definitions.ts
 */

import fs from "fs";
import path from "path";

// ---------------------------------------------------------------------------
// 1. TOOL DEFINITIONS (the schemas the LLM receives)
// ---------------------------------------------------------------------------

/**
 * Anthropic tool schema — this is what you pass in the `tools` array
 * to client.messages.create(). The LLM uses these descriptions to decide
 * when and how to call each tool.
 */
interface AnthropicTool {
  name: string;
  description: string;
  input_schema: {
    type: "object";
    properties: Record<string, { type: string; description: string }>;
    required: string[];
  };
}

export const SCOUT_TOOLS: AnthropicTool[] = [
  {
    name: "search_datasets",
    description: [
      "Search the Scout schema index for datasets relevant to a natural language query.",
      "Returns the top matching dataset schemas to use when writing SQL.",
      "Always call this before writing SQL so you know which table names and column names are available.",
      "Returns a JSON array of {dataset_id, chunk_type, text} objects.",
    ].join(" "),
    input_schema: {
      type: "object",
      properties: {
        query: {
          type: "string",
          description:
            "Natural language description of what you are looking for, e.g. 'coffee shops' or 'building heights'",
        },
      },
      required: ["query"],
    },
  },
  {
    name: "execute_sql",
    description: [
      "Execute a DuckDB SQL SELECT statement against the Scout geospatial database.",
      "The database contains GeoParquet files accessible via HTTPFS from S3.",
      "Always start with LOAD spatial; before any spatial function calls.",
      "Returns a JSON object with {row_count, columns, sample_rows (up to 5)} so you can inspect the result.",
      "If the query fails, the error message is returned — use it to diagnose and retry with get_schema if needed.",
    ].join(" "),
    input_schema: {
      type: "object",
      properties: {
        sql: {
          type: "string",
          description:
            "A complete, valid DuckDB SQL SELECT statement. Must start with 'LOAD spatial;' on its own line.",
        },
      },
      required: ["sql"],
    },
  },
  {
    name: "get_map_extent",
    description: [
      "Returns the current map viewport bounding box as {west, south, east, north} in WGS84 degrees.",
      "Use this to automatically scope queries to the area the user is currently viewing.",
      "Example: 'Show me restaurants' implicitly means 'in the current map view'.",
      "Always call this for queries that don't specify a specific place name.",
    ].join(" "),
    input_schema: {
      type: "object",
      properties: {},
      required: [],
    },
  },
  {
    name: "ask_clarification",
    description: [
      "Ask the user a clarifying question when the query is genuinely ambiguous.",
      "Only use this when the ambiguity would materially change the SQL (e.g. different spatial scope, different dataset).",
      "Prefer making a reasonable assumption and noting it in your response over asking for clarification.",
      "Returns the user's text response.",
    ].join(" "),
    input_schema: {
      type: "object",
      properties: {
        question: {
          type: "string",
          description: "The clarifying question to ask the user, in plain English.",
        },
      },
      required: ["question"],
    },
  },
];

// ---------------------------------------------------------------------------
// 2. TOOL HANDLER FUNCTIONS
// ---------------------------------------------------------------------------

/** Loads retrieval_index.json from the Python exercise output */
function loadRetrievalIndex(): {
  documents: Array<{ id: string; document: string; metadata: Record<string, unknown> }>;
} {
  const candidatePaths = [
    path.join(process.cwd(), "public", "data", "retrieval_index.json"),
    path.join(__dirname, "..", "26-vector-rag", "output", "retrieval_index.json"),
  ];
  for (const p of candidatePaths) {
    if (fs.existsSync(p)) {
      return JSON.parse(fs.readFileSync(p, "utf-8"));
    }
  }
  throw new Error("retrieval_index.json not found — run Module 26 Exercise 3 first.");
}

/**
 * search_datasets handler
 * Performs keyword overlap scoring against the retrieval index.
 */
export function handleSearchDatasets(query: string): string {
  let index: ReturnType<typeof loadRetrievalIndex>;
  try {
    index = loadRetrievalIndex();
  } catch (e) {
    return JSON.stringify({ error: String(e) });
  }

  const queryTokens = new Set(query.toLowerCase().split(/\W+/).filter(Boolean));
  const scored = index.documents.map((doc) => {
    const docTokens = doc.document.toLowerCase().split(/\W+/).filter(Boolean);
    let hits = 0;
    for (const token of docTokens) {
      if (queryTokens.has(token)) hits++;
    }
    const score = queryTokens.size > 0 ? hits / queryTokens.size : 0;
    return { doc, score };
  });

  const topK = scored
    .sort((a, b) => b.score - a.score)
    .slice(0, 3)
    .filter((item) => item.score > 0)
    .map(({ doc, score }) => ({
      dataset_id: String(doc.metadata.dataset_id ?? "?"),
      chunk_type: String(doc.metadata.chunk_type ?? "?"),
      similarity: Math.round(score * 1000) / 1000,
      text: doc.document.slice(0, 300),
    }));

  return JSON.stringify(topK, null, 2);
}

/**
 * execute_sql handler — SERVER-SIDE STUB
 *
 * In Scout, DuckDB-Wasm runs in the BROWSER. The server can't call it directly.
 * For this exercise, we return a structured mock so you can see the message flow.
 * In Exercise 3 (multi-step agent), the route streams SQL back to the browser
 * which executes it and returns the result to the agent via a second API call.
 *
 * In production: look at how Databricks Genie handles this — it runs SQL
 * server-side via a cluster connection. Scout takes the browser-first approach.
 */
export function handleExecuteSql(sql: string): string {
  // In this exercise, we return a mock result to show the message format.
  // Exercise 3 wires this to the real DuckDB-Wasm result via browser bridge.
  return JSON.stringify({
    _note: "SERVER-SIDE STUB — real execution happens in DuckDB-Wasm (browser).",
    _sql_received: sql.slice(0, 100) + (sql.length > 100 ? "..." : ""),
    row_count: 42,
    columns: ["id", "name", "category", "lat", "lon"],
    sample_rows: [
      { id: "abc123", name: "Blue Bottle Coffee", category: "coffee_shop", lat: 37.771, lon: -122.412 },
    ],
  });
}

/**
 * get_map_extent handler — returns a default SF bbox.
 * In the real Scout UI, this reads `map.getBounds()` from MapLibre.
 * The actual Next.js route receives the current bbox from the frontend.
 */
export function handleGetMapExtent(bbox?: {
  west: number; south: number; east: number; north: number;
}): string {
  const extent = bbox ?? {
    west: -122.5152,
    south: 37.7079,
    east: -122.3591,
    north: 37.8324,
    _note: "Default SF bounding box — in Scout UI, this reads the live map viewport.",
  };
  return JSON.stringify(extent);
}

/**
 * ask_clarification handler — in the real UI, this surfaces a dialog.
 * For the exercise, returns a hardcoded response.
 */
export function handleAskClarification(question: string): string {
  console.log(`\n  [ASK_CLARIFICATION] Agent asks: "${question}"`);
  console.log(`  [ASK_CLARIFICATION] (Simulated user answer: "All of San Francisco")`);
  return JSON.stringify({ user_response: "All of San Francisco" });
}

/** Routes a tool_use block to the correct handler function */
export function dispatchTool(
  name: string,
  input: Record<string, unknown>,
  context?: { bbox?: { west: number; south: number; east: number; north: number } }
): string {
  switch (name) {
    case "search_datasets":
      return handleSearchDatasets(input.query as string);
    case "execute_sql":
      return handleExecuteSql(input.sql as string);
    case "get_map_extent":
      return handleGetMapExtent(context?.bbox);
    case "ask_clarification":
      return handleAskClarification(input.question as string);
    default:
      return JSON.stringify({ error: `Unknown tool: ${name}` });
  }
}

// ---------------------------------------------------------------------------
// 3. DRY RUN — shows the full message flow without making an LLM API call
// ---------------------------------------------------------------------------

interface Message {
  role: "user" | "assistant";
  content: unknown;
}

/**
 * Simulates a two-turn tool-calling exchange to demonstrate the protocol.
 *
 * Real flow (Anthropic):
 *   Turn 1: POST /v1/messages with tools → response.stop_reason === "tool_use"
 *   Turn 2: Append tool result → POST /v1/messages again → response.stop_reason === "end_turn"
 *
 * We mock the assistant turns so you can see the exact JSON shapes.
 */
function simulatedAgentLoop(userQuery: string): void {
  console.log("\n" + "=".repeat(65));
  console.log("SIMULATED AGENT LOOP (no API call — mocked assistant turns)");
  console.log("=".repeat(65));
  console.log(`\nUser query: "${userQuery}"\n`);

  const messages: Message[] = [{ role: "user", content: userQuery }];

  // ---- TURN 1: LLM would return a tool_use block ----
  // In reality: const response = await client.messages.create({ messages, tools: SCOUT_TOOLS, ... })
  const mockToolUse = {
    type: "tool_use",
    id: "toolu_mock_001",
    name: "search_datasets",
    input: { query: userQuery },
  };

  console.log("TURN 1 → Sending to LLM:");
  console.log(JSON.stringify({ tools: SCOUT_TOOLS.map(t => t.name), messages }, null, 2).slice(0, 600) + "...\n");

  console.log("TURN 1 ← LLM returns (stop_reason: tool_use):");
  console.log(JSON.stringify({ stop_reason: "tool_use", content: [mockToolUse] }, null, 2));

  // ---- Execute the tool ----
  const toolResult = dispatchTool(mockToolUse.name, mockToolUse.input);
  console.log("\nTool executed. Result (first 300 chars):");
  console.log(toolResult.slice(0, 300));

  // Append assistant turn + tool result to messages
  messages.push({ role: "assistant", content: [mockToolUse] });
  messages.push({
    role: "user",
    content: [{ type: "tool_result", tool_use_id: mockToolUse.id, content: toolResult }],
  });

  // ---- TURN 2: LLM would return the final SQL ----
  const mockFinalSql = `LOAD spatial;\nSELECT id, name, category, lat, lon FROM places WHERE category IN ('coffee_shop') LIMIT 200;`;
  console.log("\nTURN 2 → Sending messages (now includes tool_result):");
  console.log(`  Total messages in context: ${messages.length}`);
  console.log("\nTURN 2 ← LLM returns (stop_reason: end_turn):");
  console.log(mockFinalSql);

  console.log("\n" + "=".repeat(65));
  console.log("KEY OBSERVATIONS:");
  console.log("  1. Message array grows with each tool turn");
  console.log("  2. tool_use block MUST be echoed back in the assistant role");
  console.log("  3. tool_result MUST reference the same tool_use_id");
  console.log("  4. Multi-step agent = repeat this loop until stop_reason === 'end_turn'");
  console.log("=".repeat(65) + "\n");
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

if (import.meta.url === `file://${process.argv[1]}`) {
  console.log("Scout Exercise 1: Tool Definitions");
  console.log("=".repeat(65));
  console.log(`\nDefined ${SCOUT_TOOLS.length} tools:`);
  for (const tool of SCOUT_TOOLS) {
    const required = tool.input_schema.required.join(", ") || "(none)";
    console.log(`  ${tool.name.padEnd(25)} required args: ${required}`);
  }

  // Test each handler
  console.log("\n--- Handler tests ---");
  console.log("\nsearch_datasets('coffee shops near parks'):"); 
  try {
    const result = handleSearchDatasets("coffee shops near parks");
    console.log(result.slice(0, 400));
  } catch (e) {
    console.log(`  (Index not available — run Module 26 first): ${e}`);
  }

  console.log("\nexecute_sql stub:");
  console.log(handleExecuteSql("LOAD spatial;\nSELECT * FROM places LIMIT 5;").slice(0, 200));

  console.log("\nget_map_extent (default SF bbox):");
  console.log(handleGetMapExtent());

  // Simulated agent loop
  simulatedAgentLoop("Show me coffee shops near Dolores Park");
}
