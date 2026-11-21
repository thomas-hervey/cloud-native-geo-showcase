/**
 * Scout Exercise 2: Single-Step Agent Baseline
 * =========================================================
 * A minimal agent that makes exactly ONE tool call (search_datasets),
 * then uses the retrieved schema to write SQL — equivalent to Module 26
 * RAG but now the LLM decides when to call the tool.
 *
 * Learning goal: Compare this output to the Module 26 RAG route.
 * The SQL should be nearly identical; what changes is:
 *   - Module 26 RAG: we hardcode "retrieve schema → build prompt → call LLM"
 *   - Module 27 agent: the LLM decides to call search_datasets, reads the result,
 *     then writes SQL — the application code has NO hardcoded pipeline steps
 *
 * Run:
 *   export ANTHROPIC_API_KEY=sk-...
 *   npx tsx src/exercises/agentic/02_single_step_agent.ts
 *
 * Cost: ~$0.003 per query (one tool call + one SQL generation)
 */

import Anthropic from "@anthropic-ai/sdk";
import { SCOUT_TOOLS, handleSearchDatasets } from "./01_tool_definitions";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

// ---------------------------------------------------------------------------
// Single-step agent
// ---------------------------------------------------------------------------

interface AgentResult {
  sql: string;
  input_tokens: number;
  output_tokens: number;
  tool_calls_made: number;
  tool_calls: Array<{ tool: string; query: string; result_preview: string }>;
}

/**
 * Runs a minimal agent that:
 * 1. Receives the user query
 * 2. Decides to call search_datasets (we constrain it to only this tool)
 * 3. Gets the schema result
 * 4. Returns the final SQL
 *
 * We constrain to search_datasets only so we can guarantee single-step behavior.
 * Exercise 3 enables all tools.
 */
async function runSingleStepAgent(userQuery: string): Promise<AgentResult> {
  const singleTool = SCOUT_TOOLS.filter((t) => t.name === "search_datasets");

  const messages: Anthropic.MessageParam[] = [
    { role: "user", content: userQuery },
  ];

  let totalInputTokens = 0;
  let totalOutputTokens = 0;
  const toolCalls: AgentResult["tool_calls"] = [];

  const systemPrompt = `You are Scout, a geospatial SQL assistant.
You have access to search_datasets to find the schema for the data you need.
Always call search_datasets BEFORE writing any SQL.
Return ONLY valid DuckDB SQL starting with LOAD spatial; — no explanation needed.`;

  // Turn 1: Agent calls search_datasets
  const turn1 = await client.messages.create({
    model: "claude-opus-4-5",
    max_tokens: 1024,
    system: systemPrompt,
    tools: singleTool,
    messages,
  });

  totalInputTokens += turn1.usage.input_tokens;
  totalOutputTokens += turn1.usage.output_tokens;

  if (turn1.stop_reason !== "tool_use") {
    // Agent returned SQL directly without calling the tool — unusual but handle it
    const text = turn1.content.find((b) => b.type === "text");
    return {
      sql: text?.type === "text" ? text.text : "(no SQL returned)",
      input_tokens: totalInputTokens,
      output_tokens: totalOutputTokens,
      tool_calls_made: 0,
      tool_calls: [],
    };
  }

  const toolUseBlock = turn1.content.find((b) => b.type === "tool_use");
  if (!toolUseBlock || toolUseBlock.type !== "tool_use") {
    throw new Error("Expected tool_use block not found");
  }

  // Execute the tool
  const toolInput = toolUseBlock.input as { query: string };
  const toolResult = handleSearchDatasets(toolInput.query);

  toolCalls.push({
    tool: toolUseBlock.name,
    query: toolInput.query,
    result_preview: toolResult.slice(0, 200),
  });

  // Append Turn 1 result and tool output
  messages.push({ role: "assistant", content: turn1.content });
  messages.push({
    role: "user",
    content: [{ type: "tool_result", tool_use_id: toolUseBlock.id, content: toolResult }],
  });

  // Turn 2: Agent writes the final SQL
  const turn2 = await client.messages.create({
    model: "claude-opus-4-5",
    max_tokens: 1024,
    system: systemPrompt,
    tools: singleTool,
    messages,
  });

  totalInputTokens += turn2.usage.input_tokens;
  totalOutputTokens += turn2.usage.output_tokens;

  const finalText = turn2.content.find((b) => b.type === "text");
  const sql = finalText?.type === "text"
    ? finalText.text.trim()
    : "(no SQL in response)";

  return {
    sql,
    input_tokens: totalInputTokens,
    output_tokens: totalOutputTokens,
    tool_calls_made: 1,
    tool_calls: toolCalls,
  };
}

// ---------------------------------------------------------------------------
// Test against the same queries used in Module 26 Exercise 2
// ---------------------------------------------------------------------------

const TEST_QUERIES = [
  "Show me coffee shops near Dolores Park",
  "Find all parks in the Marina district",
  "Where are the breweries in SF?",
  "Show me tall buildings in SoMa",
];

async function main() {
  console.log("Scout Exercise 2: Single-Step Agent Baseline");
  console.log("=".repeat(65));
  console.log(
    "\nCompare these results to Module 26 Exercise 2 (retrieval_compare.py)."
  );
  console.log(
    "The SQL should be semantically equivalent — what differs is the pipeline.\n"
  );

  for (const query of TEST_QUERIES) {
    console.log(`\nQuery: "${query}"`);
    console.log("-".repeat(50));

    try {
      const result = await runSingleStepAgent(query);

      console.log(`Tool calls made: ${result.tool_calls_made}`);
      if (result.tool_calls.length > 0) {
        const call = result.tool_calls[0];
        console.log(`  search_datasets("${call.query}")`);
        console.log(`  Result preview: ${call.result_preview.slice(0, 120)}...`);
      }
      console.log(`\nGenerated SQL:\n${result.sql}`);
      console.log(`\nTokens: ${result.input_tokens} in + ${result.output_tokens} out = ${result.input_tokens + result.output_tokens} total`);
    } catch (err) {
      console.error(`  Error: ${err}`);
    }

    // Small delay to avoid rate limiting
    await new Promise((r) => setTimeout(r, 1000));
  }

  console.log("\n" + "=".repeat(65));
  console.log("KEY OBSERVATIONS TO RECORD:");
  console.log("  1. The agent chose search_datasets before writing SQL — we didn't instruct it to.");
  console.log("  2. Token cost is roughly 2x the direct prompt approach (two API calls).");
  console.log("  3. The search query the agent used may differ from the user's phrasing.");
  console.log("  4. SQL coverage should be comparable to Module 26 RAG output.");
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(console.error);
}
