/**
 * Agentic GIS — Exercise 2: MCP Client Agent
 * ================================================
 * Builds the *client* side of the MCP pattern: an agentic loop where Claude
 * decides which tools to call, the MCP SDK client executes them against the
 * Exercise 1 server, and results feed back into Claude until it has a complete
 * answer.
 *
 * Compare to Exercise 1 (the server):
 *   01_mcp_server.ts  — exposes tools over stdio JSON-RPC
 *   02_langgraph_agent.ts — discovers and calls those tools as an LLM agent
 *
 * Architecture:
 *   [this process]  →  spawns subprocess  →  [01_mcp_server.ts]
 *   StdioClientTransport sends JSON-RPC over stdin/stdout of the child process
 *
 * Key concepts:
 *   - client.listTools()  → dynamic tool discovery (no hardcoded schemas)
 *   - Anthropic tool_use / tool_result message loop
 *   - MCP tools mapped to Anthropic tool format at runtime
 *   - Self-correction: Claude reads error responses and retries with better args
 *   - max_iterations guard prevents infinite loops
 *
 * Run:
 *   npx tsx src/exercises/agentic-gis/02_langgraph_agent.ts \
 *     --query "coffee shops within 500m of Dolores Park"
 *
 * Options:
 *   --query  <string>   Natural language question (required)
 *   --model  <string>   Anthropic model ID (default: claude-sonnet-4-6)
 *   --max-steps <n>     Max agent iterations before hard stop (default: 8)
 */

import { config } from 'dotenv';
import path from 'path';

const projectRoot = path.resolve(__dirname, '..', '..', '..');
config({ path: path.join(projectRoot, '.env.local') });

import Anthropic from '@anthropic-ai/sdk';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

// ---------------------------------------------------------------------------
// CLI argument parsing
// ---------------------------------------------------------------------------

function parseArgs(): { query: string; model: string; maxSteps: number } {
  const args = process.argv.slice(2);
  let query = '';
  let model = 'claude-sonnet-4-6';
  let maxSteps = 8;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--query' && args[i + 1]) query = args[++i];
    if (args[i] === '--model' && args[i + 1]) model = args[++i];
    if (args[i] === '--max-steps' && args[i + 1]) maxSteps = parseInt(args[++i], 10);
  }

  if (!query) {
    console.error('Usage: npx tsx 02_langgraph_agent.ts --query "<your question>"');
    process.exit(1);
  }
  return { query, model, maxSteps };
}

// ---------------------------------------------------------------------------
// Tool format conversion
// ---------------------------------------------------------------------------

// MCP returns tools with `inputSchema` (camelCase).
// Anthropic expects `input_schema` (snake_case).
// Map between them so Claude receives well-formed tool definitions.

interface McpToolDefinition {
  name: string;
  description?: string;
  inputSchema: {
    type: string;
    properties?: Record<string, unknown>;
    required?: string[];
  };
}

function toAnthropicTool(mcp: McpToolDefinition): Anthropic.Tool {
  return {
    name: mcp.name,
    description: mcp.description ?? '',
    input_schema: {
      type: 'object',
      properties: mcp.inputSchema.properties ?? {},
      required: mcp.inputSchema.required ?? [],
    },
  };
}

// ---------------------------------------------------------------------------
// Reasoning trace helpers
// ---------------------------------------------------------------------------

// All trace output goes to stderr so stdout stays clean for pipe-friendly use.
// Format: [Step N] → tool call, ↳ result summary

function printHeader(query: string, model: string) {
  const width = 64;
  const border = '═'.repeat(width);
  process.stderr.write(`\n╔${border}╗\n`);
  process.stderr.write(`║  Scout Geo Agent — MCP Client${' '.repeat(width - 30)}║\n`);
  const modelLine = `  Model: ${model}`;
  process.stderr.write(`║${modelLine}${' '.repeat(width - modelLine.length)}║\n`);
  const qLine = `  Query: "${query}"`;
  const truncated = qLine.length > width ? qLine.slice(0, width - 3) + '...' : qLine;
  process.stderr.write(`║${truncated}${' '.repeat(Math.max(0, width - truncated.length))}║\n`);
  process.stderr.write(`╚${border}╝\n\n`);
}

function printStep(step: number, toolName: string, input: Record<string, unknown>) {
  const inputStr = Object.keys(input).length
    ? `  { ${Object.entries(input).map(([k, v]) => `${k}: "${String(v).slice(0, 60)}"`).join(', ')} }`
    : '  (no input)';
  process.stderr.write(`[Step ${step}] Claude → ${toolName}\n${inputStr}\n`);
}

function printResult(text: string) {
  // Show just the first 200 chars of the result so the trace stays readable.
  const preview = text.length > 200 ? text.slice(0, 200) + ' …(truncated)' : text;
  process.stderr.write(`  ↳ ${preview.replace(/\n/g, '\n     ')}\n\n`);
}

function printDone(steps: number, stopReason: string, elapsed: number) {
  process.stderr.write(`[Done] stop_reason: ${stopReason}  (${steps} step${steps !== 1 ? 's' : ''}, ${(elapsed / 1000).toFixed(1)}s)\n\n`);
}

function printFinalSql(sql: string) {
  const divider = '─'.repeat(64);
  process.stderr.write(`${divider}\n`);
  process.stderr.write(`Generated SQL\n`);
  process.stderr.write(`${divider}\n`);
  // SQL goes to stdout so it can be piped or captured
  process.stdout.write(sql + '\n');
  process.stderr.write(`${divider}\n\n`);
}

// ---------------------------------------------------------------------------
// Extract the final SQL from the last assistant message
// ---------------------------------------------------------------------------

function extractSql(messages: Anthropic.Messages.MessageParam[]): string | null {
  // Walk the message history backwards to find the last assistant text block
  for (let i = messages.length - 1; i >= 0; i--) {
    const msg = messages[i];
    if (msg.role === 'assistant') {
      const content = Array.isArray(msg.content) ? msg.content : [msg.content];
      for (const block of content) {
        if (typeof block === 'object' && block !== null && 'type' in block && block.type === 'text') {
          const text = (block as Anthropic.Messages.TextBlock).text;
          // Look for a fenced SQL block first
          const fenced = text.match(/```(?:sql)?\s*([\s\S]+?)```/i);
          if (fenced) return fenced[1].trim();
          // Otherwise look for LOAD spatial or SELECT as the start of bare SQL
          const bare = text.match(/(LOAD\s+spatial[\s\S]+|SELECT\s+[\s\S]+)/i);
          if (bare) return bare[1].trim();
          // Return the raw text if it looks like SQL at all
          if (text.includes('SELECT') || text.includes('LOAD spatial')) return text.trim();
        }
      }
    }
  }
  // Fallback: check tool results for query_places output
  for (let i = messages.length - 1; i >= 0; i--) {
    const msg = messages[i];
    if (msg.role === 'user' && Array.isArray(msg.content)) {
      for (const block of msg.content) {
        if (
          typeof block === 'object' &&
          block !== null &&
          'type' in block &&
          block.type === 'tool_result'
        ) {
          const toolResult = block as Anthropic.Messages.ToolResultBlockParam;
          const text = Array.isArray(toolResult.content)
            ? toolResult.content.map((c) => (typeof c === 'string' ? c : 'text' in c ? c.text : '')).join('')
            : String(toolResult.content ?? '');
          try {
            const parsed = JSON.parse(text) as { sql?: string };
            if (parsed.sql) return parsed.sql;
          } catch {
            // not JSON — ignore
          }
        }
      }
    }
  }
  return null;
}

// ---------------------------------------------------------------------------
// Main agent loop
// ---------------------------------------------------------------------------

async function runAgent() {
  const { query, model, maxSteps } = parseArgs();
  const startTime = Date.now();

  // ------------------------------------------------------------------
  // 1. Start the MCP client and connect to the Exercise 1 server.
  //    StdioClientTransport spawns 01_mcp_server.ts as a child process.
  //    The client communicates with it over stdin/stdout JSON-RPC.
  // ------------------------------------------------------------------

  const serverPath = path.join(__dirname, '01_mcp_server.ts');

  const transport = new StdioClientTransport({
    command: 'npx',
    args: ['tsx', serverPath],
    env: {
      ...process.env,
      // Ensure the child process inherits the API key
      ANTHROPIC_API_KEY: process.env.ANTHROPIC_API_KEY ?? '',
    },
  });

  const mcpClient = new Client(
    { name: 'scout-geo-agent', version: '1.0.0' },
    { capabilities: {} }
  );

  await mcpClient.connect(transport);

  // ------------------------------------------------------------------
  // 2. Discover tools at runtime via tools/list.
  //    This is the key MCP behaviour: the client learns what tools exist
  //    from the server, not from hardcoded definitions in this file.
  //    Compare to the LangChain exercise where tool schemas lived in the client.
  // ------------------------------------------------------------------

  const { tools: mcpTools } = await mcpClient.listTools();
  const anthropicTools = (mcpTools as McpToolDefinition[]).map(toAnthropicTool);

  printHeader(query, model);
  process.stderr.write(`Discovered ${anthropicTools.length} tools: ${anthropicTools.map((t) => t.name).join(', ')}\n\n`);

  // ------------------------------------------------------------------
  // 3. Initialise the Anthropic client and message history.
  // ------------------------------------------------------------------

  const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

  const systemPrompt = `You are a geospatial query assistant for San Francisco.
Your job is to translate a natural language question into a DuckDB SQL query
using the available MCP tools.

Workflow:
1. Call list_datasets to see what data is available.
2. Call explain_schema on the relevant dataset to get column names.
3. Call query_places with the user's question to generate SQL.
4. If query_places returns an error or the SQL looks wrong, call explain_schema
   again to verify column names, then retry query_places.
5. When you have a valid SQL query, stop and present it clearly.

Always end your final response with the SQL query in a fenced \`\`\`sql block.`;

  const messages: Anthropic.Messages.MessageParam[] = [
    { role: 'user', content: query },
  ];

  // ------------------------------------------------------------------
  // 4. Agentic loop.
  //    Each iteration: Claude responds (possibly with tool_use blocks) →
  //    we execute the tool calls via the MCP client → append results →
  //    repeat until stop_reason === 'end_turn' or max steps reached.
  // ------------------------------------------------------------------

  let step = 0;
  let stopReason = 'unknown';

  while (step < maxSteps) {
    const response = await anthropic.messages.create({
      model,
      max_tokens: 1024,
      system: systemPrompt,
      tools: anthropicTools,
      messages,
    });

    // Append the assistant's full response to history so Claude has context.
    messages.push({ role: 'assistant', content: response.content });

    stopReason = response.stop_reason ?? 'unknown';

    if (stopReason === 'end_turn') {
      // Claude is done — no more tool calls.
      break;
    }

    if (stopReason !== 'tool_use') {
      process.stderr.write(`[Warn] Unexpected stop_reason: ${stopReason}\n`);
      break;
    }

    // ------------------------------------------------------------------
    // 5. Execute tool calls.
    //    For each tool_use block in Claude's response, call the MCP server
    //    via client.callTool() and collect results as tool_result blocks.
    // ------------------------------------------------------------------

    const toolResults: Anthropic.Messages.ToolResultBlockParam[] = [];

    for (const block of response.content) {
      if (block.type !== 'tool_use') continue;

      step++;
      printStep(step, block.name, block.input as Record<string, unknown>);

      let resultText: string;
      try {
        const mcpResult = await mcpClient.callTool({
          name: block.name,
          arguments: block.input as Record<string, unknown>,
        });

        // MCP tool results contain a `content` array of typed blocks.
        // We extract the text content for Anthropic's tool_result format.
        resultText = (mcpResult.content as Array<{ type: string; text?: string }>)
          .filter((c) => c.type === 'text')
          .map((c) => c.text ?? '')
          .join('\n');

        printResult(resultText);
      } catch (err) {
        resultText = `Tool execution error: ${err instanceof Error ? err.message : String(err)}`;
        process.stderr.write(`  ✗ ${resultText}\n\n`);
      }

      toolResults.push({
        type: 'tool_result',
        tool_use_id: block.id,
        content: resultText,
      });
    }

    // Append tool results as a user turn so Claude can read them next iteration.
    messages.push({ role: 'user', content: toolResults });
  }

  if (step >= maxSteps) {
    process.stderr.write(`[Warn] Reached max steps (${maxSteps}). Stopping.\n\n`);
    stopReason = 'max_steps';
  }

  const elapsed = Date.now() - startTime;
  printDone(step, stopReason, elapsed);

  // ------------------------------------------------------------------
  // 6. Extract and print the final SQL.
  // ------------------------------------------------------------------

  const sql = extractSql(messages);
  if (sql) {
    printFinalSql(sql);
  } else {
    process.stderr.write('[Warn] No SQL found in agent output.\n');
    // Print the last assistant message in full as a fallback
    const lastAssistant = [...messages].reverse().find((m) => m.role === 'assistant');
    if (lastAssistant) {
      const content = Array.isArray(lastAssistant.content)
        ? lastAssistant.content
        : [lastAssistant.content];
      for (const block of content) {
        if (typeof block === 'object' && 'type' in block && block.type === 'text') {
          process.stdout.write((block as Anthropic.Messages.TextBlock).text + '\n');
        }
      }
    }
  }

  await mcpClient.close();
}

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

runAgent().catch((err) => {
  process.stderr.write(`[Fatal] ${err instanceof Error ? err.message : String(err)}\n`);
  process.exit(1);
});
