/**
 * Scout Exercise 3: Observability & Reasoning Trace Logger
 * =====================================================================
 * Wraps the agent loop with structured logging so every tool call is
 * captured, timed, and emitted as a JSON trace.
 *
 * This is the production observability pattern:
 *   - Every tool call: name, input, output summary, elapsed_ms, tokens
 *   - Every LLM turn: model, tokens, stop_reason, timestamp
 *   - Final result: sql, total_cost_estimate, total_elapsed_ms
 *
 * In production systems (Langfuse, LangSmith, Baseten Traces) this trace
 * is what you load when a user reports "the agent gave me a wrong query."
 *
 * Run:
 *   export ANTHROPIC_API_KEY=sk-...
 *   npx tsx src/exercises/agentic/03_observability.ts
 *   # Add --json to emit machine-readable trace to stdout
 */

import Anthropic from "@anthropic-ai/sdk";
import { SCOUT_TOOLS, dispatchTool } from "./01_tool_definitions";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

// ---------------------------------------------------------------------------
// Trace types
// ---------------------------------------------------------------------------

export interface ToolCallSpan {
  span_type: "tool_call";
  step: number;
  tool: string;
  input: Record<string, unknown>;
  output_summary: string;   // first 200 chars of output
  output_length: number;    // full char count
  elapsed_ms: number;
  timestamp: string;
}

export interface LlmTurnSpan {
  span_type: "llm_turn";
  turn: number;
  model: string;
  stop_reason: string;
  input_tokens: number;
  output_tokens: number;
  elapsed_ms: number;
  timestamp: string;
}

export type Span = ToolCallSpan | LlmTurnSpan;

export interface AgentTrace {
  query: string;
  spans: Span[];
  final_sql: string | null;
  total_input_tokens: number;
  total_output_tokens: number;
  total_elapsed_ms: number;
  estimated_cost_usd: number;  // rough Claude Sonnet pricing
  success: boolean;
  error?: string;
}

// Claude Sonnet 3.5 pricing ($ per million tokens, as of early 2025)
// Update this whenever pricing changes — it's the "per query cost" metric
const PRICE_PER_M_INPUT = 3.0;
const PRICE_PER_M_OUTPUT = 15.0;

function estimateCost(inputTokens: number, outputTokens: number): number {
  return (
    (inputTokens / 1_000_000) * PRICE_PER_M_INPUT +
    (outputTokens / 1_000_000) * PRICE_PER_M_OUTPUT
  );
}

// ---------------------------------------------------------------------------
// Instrumented agent loop
// ---------------------------------------------------------------------------

const SYSTEM_PROMPT = `You are Scout, a geospatial SQL assistant. 
Use the available tools to find the right schema then write SQL.
You can call search_datasets, get_map_extent, or ask_clarification.
Execute your reasoning in 3 or fewer tool calls, then return the final SQL.
Start every SQL with LOAD spatial;`;

export async function runInstrumentedAgent(query: string): Promise<AgentTrace> {
  const traceStart = Date.now();
  const spans: Span[] = [];
  const messages: Anthropic.MessageParam[] = [
    { role: "user", content: query },
  ];

  let totalInputTokens = 0;
  let totalOutputTokens = 0;
  let finalSql: string | null = null;
  let error: string | undefined;
  let turn = 0;
  const MAX_TURNS = 6;

  try {
    while (turn < MAX_TURNS) {
      turn++;
      const llmStart = Date.now();

      const response = await client.messages.create({
        model: "claude-opus-4-5",
        max_tokens: 2048,
        system: SYSTEM_PROMPT,
        tools: SCOUT_TOOLS,
        messages,
      });

      const llmElapsed = Date.now() - llmStart;

      spans.push({
        span_type: "llm_turn",
        turn,
        model: response.model,
        stop_reason: response.stop_reason ?? "unknown",
        input_tokens: response.usage.input_tokens,
        output_tokens: response.usage.output_tokens,
        elapsed_ms: llmElapsed,
        timestamp: new Date().toISOString(),
      });

      totalInputTokens += response.usage.input_tokens;
      totalOutputTokens += response.usage.output_tokens;

      if (response.stop_reason === "end_turn") {
        const textBlock = response.content.find((b) => b.type === "text");
        if (textBlock?.type === "text") {
          const sqlMatch = textBlock.text.match(/LOAD spatial;[\s\S]+/i);
          finalSql = sqlMatch ? sqlMatch[0].trim() : textBlock.text.trim();
        }
        break;
      }

      if (response.stop_reason !== "tool_use") break;

      messages.push({ role: "assistant", content: response.content });

      const toolResults: Anthropic.ToolResultBlockParam[] = [];

      for (const block of response.content) {
        if (block.type !== "tool_use") continue;

        const toolStart = Date.now();
        const input = block.input as Record<string, unknown>;
        const output = dispatchTool(block.name, input);
        const toolElapsed = Date.now() - toolStart;

        // Capture SQL before it's replaced in subsequent iterations  
        if (block.name === "execute_sql") {
          finalSql = input.sql as string;
        }

        spans.push({
          span_type: "tool_call",
          step: spans.filter((s) => s.span_type === "tool_call").length + 1,
          tool: block.name,
          input,
          output_summary: output.slice(0, 200),
          output_length: output.length,
          elapsed_ms: toolElapsed,
          timestamp: new Date().toISOString(),
        });

        toolResults.push({
          type: "tool_result",
          tool_use_id: block.id,
          content: output,
        });
      }

      messages.push({ role: "user", content: toolResults });
    }
  } catch (err) {
    error = err instanceof Error ? err.message : String(err);
  }

  return {
    query,
    spans,
    final_sql: finalSql,
    total_input_tokens: totalInputTokens,
    total_output_tokens: totalOutputTokens,
    total_elapsed_ms: Date.now() - traceStart,
    estimated_cost_usd: estimateCost(totalInputTokens, totalOutputTokens),
    success: !error && finalSql !== null,
    error,
  };
}

// ---------------------------------------------------------------------------
// Pretty-print trace for terminal display
// ---------------------------------------------------------------------------

function printTrace(trace: AgentTrace): void {
  console.log(`\n${"=".repeat(65)}`);
  console.log(`Query: "${trace.query}"`);
  console.log(`Status: ${trace.success ? "✅ SUCCESS" : "❌ FAILED"}`);
  if (trace.error) console.log(`Error: ${trace.error}`);
  console.log("-".repeat(65));

  for (const span of trace.spans) {
    if (span.span_type === "llm_turn") {
      console.log(
        `  🤖 LLM turn ${span.turn}: ${span.stop_reason} | ` +
        `${span.input_tokens}↑ ${span.output_tokens}↓ tokens | ${span.elapsed_ms}ms`
      );
    } else {
      console.log(
        `  🔧 Step ${span.step}: ${span.tool.padEnd(20)} ${span.elapsed_ms}ms`
      );
      const inputDesc = Object.entries(span.input)
        .map(([k, v]) => `${k}="${String(v).slice(0, 40)}"`)
        .join(", ");
      console.log(`      Input:  ${inputDesc}`);
      console.log(`      Output: ${span.output_summary.slice(0, 100)}...`);
    }
  }

  console.log("-".repeat(65));
  console.log(`SQL:\n${trace.final_sql ?? "(none)"}`);
  console.log("-".repeat(65));
  console.log(
    `  Total: ${trace.total_elapsed_ms}ms | ` +
    `${trace.total_input_tokens}↑ ${trace.total_output_tokens}↓ tokens | ` +
    `~$${trace.estimated_cost_usd.toFixed(5)} USD`
  );
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

const OBS_TEST_QUERIES = [
  "Show me coffee shops near Dolores Park",                          // normal query — should use search_datasets once
  "Find areas with high coffee shop density",                        // multi-step — should search + execute_sql
  "Where can I find a tall building with a view over the bay?",      // might ask clarification
];

async function main() {
  const emitJson = process.argv.includes("--json");

  console.log("Scout Exercise 3: Observability & Trace Logger");
  console.log("=".repeat(65));
  if (!emitJson) {
    console.log("\nRun with --json to see the full machine-readable trace.\n");
  }

  const traces: AgentTrace[] = [];

  for (const query of OBS_TEST_QUERIES) {
    const trace = await runInstrumentedAgent(query);
    traces.push(trace);

    if (emitJson) {
      process.stdout.write(JSON.stringify(trace, null, 2) + "\n");
    } else {
      printTrace(trace);
    }

    await new Promise((r) => setTimeout(r, 1200));
  }

  if (!emitJson) {
    console.log("\n" + "=".repeat(65));
    console.log("COST SUMMARY:");
    const totalCost = traces.reduce((s, t) => s + t.estimated_cost_usd, 0);
    const totalTokens = traces.reduce(
      (s, t) => s + t.total_input_tokens + t.total_output_tokens,
      0
    );
    const avgSteps = traces.reduce(
      (s, t) => s + t.spans.filter((sp) => sp.span_type === "tool_call").length,
      0
    ) / traces.length;
    console.log(`  ${traces.length} queries | ${totalTokens.toLocaleString()} total tokens | ~$${totalCost.toFixed(5)} total`);
    console.log(`  Average tool calls per query: ${avgSteps.toFixed(1)}`);
    console.log("\nKEY OBSERVATION: Compare this per-query cost to Module 24 (direct SQL)");
    console.log("and Module 26 (RAG). Agents are significantly more expensive per query.");
    console.log("This is the latency/cost vs. capability trade-off described in the module.");
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(console.error);
}
