> **Run the server first** — opens a browser UI at `http://localhost:5173`:
>
> `npx @modelcontextprotocol/inspector npx tsx src/exercises/agentic-gis/01_mcp_server.ts`
>
> Call tools interactively before reading the rest of this module.

> **Optional background — what is the model doing under the hood?** Before
> diving into how agents call tools, open
> `src/exercises/agentic-gis/model_weights_explorer.ipynb` in VS Code. It loads
> GPT-2 (same decoder-only architecture as the models powering this module, just
> smaller) and lets you inspect the raw weight tensors — shapes, distributions,
> heatmaps. Useful for grounding the "secret sauce" intuition before treating
> the model as a black box. Select the `src/exercises/.venv` kernel when
> prompted.

## Overview

This prototype builds a GIS agent powered by the Model Context Protocol (MCP) — exposing spatial analysis tools as MCP endpoints that any compatible client (Claude Desktop, Cursor, Continue.dev, or a custom MCP SDK client) can discover and call without Scout-specific integration code. MCP standardizes how LLMs discover and invoke tools via JSON-RPC, making Scout's geospatial capabilities portable across any MCP-compatible AI workflow.

## Key Concepts

### 1. MCP Architecture: Server Exposes Tools, Client Discovers Them

An MCP server is a standalone Node.js process that registers tools using the MCP SDK and communicates over stdio or HTTP/SSE using JSON-RPC 2.0. Clients call `tools/list` at runtime to discover what tools are available — no prior knowledge required. This is the key difference from hardcoding tool schemas in an API call: the server defines the tools, and any client automatically learns what to call.

### 2. Spatial Tool Design for Agents

Scout's four MCP tools are designed so an LLM can use them in sequence without human guidance: `list_datasets` (discover what data exists), `explain_schema` (check column names before writing SQL), `query_places` (run the full RAG pipeline and return SQL), and `get_map_extent` (return the SF bounding box). The tool descriptions and Zod input schemas are the only documentation the agent receives — they must be precise enough for the LLM to call them correctly without external context.

### 3. The Agent Reasoning Loop over Spatial Data

Exercise 2 builds a client that runs a full agentic loop: call `list_datasets` to discover available data, call `explain_schema` to verify column names, call `query_places` to generate SQL, and retry with corrected schema context if the SQL fails validation. This loop mirrors what a human GIS analyst does when exploring an unfamiliar database — the agent just does it faster and without needing to read documentation manually.

In the Agentic Geo Queries module, you built a multi-turn agentic query loop using Anthropic's native
tool-calling protocol — a custom agent that speaks Claude's proprietary format.
It works, but it's coupled: only an Anthropic SDK client can drive it.

This module introduces **Model Context Protocol (MCP)**: a standardized JSON-RPC
interface that lets any compatible client — Claude Desktop, Continue.dev,
Cursor, a LangGraph graph, or your own code — discover and call the same
geospatial tools without any Scout-specific integration code.

The tools are the same. The protocol is different. The payoff is portability.

## Why MCP?

After the Agentic Geo Queries module, you have working geospatial tool-calling. MCP gives you:

| Capability            | Native Anthropic                            | MCP                                                            |
| --------------------- | ------------------------------------------- | -------------------------------------------------------------- |
| **Portability**       | Only usable by Anthropic SDK clients        | Any MCP client (Claude Desktop, Cursor, Continue.dev, custom)  |
| **Discoverability**   | Tools are hard-coded in the client          | Clients can `list_tools` at runtime; no prior knowledge needed |
| **Composability**     | One agent, one tool set                     | Chain with other MCP servers (filesystem, browser, Postgres)   |
| **Transport**         | HTTP (Next.js route)                        | stdio locally, HTTP/SSE for production                         |
| **Protocol**          | Anthropic `tool_use` / `tool_result` blocks | Standard JSON-RPC 2.0                                          |
| **Who defines tools** | You, in the LLM API call                    | You, in the MCP server — client discovers them                 |

The practical result: after this module, Claude Desktop can answer "show me
coffee shops near Dolores Park" by calling your local MCP server — without you
writing a single line of client code.

## 2. Why This Matters for Product Patterns

MCP is the emerging standard for **agentic tool interoperability**. CARTO,
Databricks, and Snowflake are all building MCP servers for their data platforms
for the same reason this module builds one for Scout:

- **Enterprise data catalogs** expose hundreds of tables. An LLM client can call
  `list_datasets` to discover what's available rather than relying on a human to
  hardcode options in a system prompt.
- **Multi-system agents** need to combine tools from different providers:
  geospatial data from Scout, web search from a Brave MCP server, internal docs
  from a filesystem MCP server. MCP makes this composable by contract.
- **The client/server separation** means your geospatial tools get better UX
  (Claude Desktop's rich interface) without you building a UI at all.

"MCP server" is the new "REST API": the interface contract that lets your data
layer integrate with any AI workflow.

---

## 3. Component Architecture

The MCP server is a **standalone Node.js process**. It has no dependency on
Next.js — it reads the same `retrieval_index.json` and calls the same Claude API
that `/api/scout/rag-query` uses, but through a completely different interface.
The server reads `public/data/retrieval_index.json` and uses Scout's RAG
pipeline constants. External clients (Claude Desktop, Cursor, a custom
LangGraph agent) communicate with it over stdio using JSON-RPC.

This is the composability payoff from the Vector Schema RAG module: you wrote the
RAG pipeline once, and it now runs inside a Next.js route AND an MCP server.

---

## Exercise 1: Build the MCP Geospatial Server

**Motivating question**: "What's the minimum code needed to expose Scout's
geospatial tools to any LLM client — without rewriting the query logic?"

The implementation is at `src/exercises/agentic-gis/01_mcp_server.ts`. The
server uses `McpServer` from `@modelcontextprotocol/sdk/server/mcp.js` — the
high-level API that handles protocol details (capability negotiation, tool
listing, call routing). You only implement the tool handlers. `StdioServerTransport`
reads JSON-RPC messages from `process.stdin` and writes responses to
`process.stdout`. All debug output must use `process.stderr.write` — anything
written to stdout becomes part of the protocol stream and will corrupt it.

Tools are registered with `server.registerTool(name, config, handler)`. The
`inputSchema` field takes a Zod shape object; the MCP SDK uses it both to
validate incoming arguments and to expose the schema in the `tools/list` response
so clients know what to pass.

Every tool handler returns `{ content: [{ type: 'text', text: string }] }`. Set
`isError: true` to signal a tool failure the LLM can read and act on.

### The four tools

**`list_datasets` (no input)** — the discovery tool. Reads
`retrieval_index.json` and returns one entry per unique `dataset_id` with a
description and bbox. A fresh LLM client calls this before anything else to
learn what data exists.

**`explain_schema(dataset_id: string)`** — finds the `schema_fields` chunk for a
dataset and formats it as a column table. An LLM uses this to avoid SQL errors
by checking column names before writing a query.

**`query_places(nl_query: string)`** — runs the full RAG pipeline: keyword
retrieval → `buildRagPrompt` → Claude → SQL string. The SQL is returned to the
client; execution happens wherever the client runs DuckDB.

**`get_map_extent` (no input)** — returns a hardcoded SF bounding box. In a full
integration, this would read `map.getBounds` from the live MapLibre viewport.
The gap between a local stdio server and a browser UI is a real architectural
challenge Exercise 2 addresses.

---

## Testing

### With mcp-inspector (recommended first test)

Run `npx @modelcontextprotocol/inspector npx tsx src/exercises/agentic-gis/01_mcp_server.ts`
and open the browser UI at `http://localhost:5173`. Verify in sequence:

1. **Tools tab** → four tools appear: `list_datasets`, `explain_schema`,
   `query_places`, `get_map_extent`
2. **`list_datasets`** → returns `sf-places-2026` and `sf-buildings-2026`
3. **`explain_schema`** with `dataset_id = "sf-places-2026"` → returns column
   table
4. **`query_places`** with `nl_query = "coffee shops near Dolores Park"` →
   returns SQL
5. **`get_map_extent`** → returns the SF bbox JSON

### With Claude Desktop

Add the server to `~/Library/Application Support/Claude/claude_desktop_config.json`
under `mcpServers`, pointing `command` at `npx` and `args` at
`["tsx", "/absolute/path/to/src/exercises/agentic-gis/01_mcp_server.ts"]` with
your `ANTHROPIC_API_KEY` in the `env` object. Restart Claude Desktop and ask:
"What geospatial data do you have access to?" — Claude will call `list_datasets`
and describe the available tables without any custom client code.

---

## What to Observe

- **Tools tab in inspector**: The tool schemas are read from the server at
  runtime via `tools/list`. The client didn't know about them in advance. This
  is discoverability in practice.

- **The `isError: true` path**: Call `explain_schema` with an invalid
  `dataset_id`. The tool returns an error listing valid IDs — not a transport
  crash. The LLM receives the error message and can retry with the right ID.
  Self-correcting behavior with no retry logic in the server.

- **stdout is protocol**: Add `console.log('debug')` to a tool handler and run
  the inspector. The JSON-RPC parse will break. The stdio transport is
  unforgiving — this is why the server uses `process.stderr.write`.

- **The same RAG pipeline in two contexts**: Open `01_mcp_server.ts` and
  `src/app/api/scout/rag-query/route.ts` side by side. `buildRagPrompt`,
  `retrieveTopK`, and `cosineSimilarity` are identical. Only the return format
  differs — `NextResponse.json` vs. MCP content block.

- **Keyword fallback in action**: The MCP server uses keyword similarity (not
  OpenAI embeddings) for retrieval. Try `query_places("pharmacies")` — the
  keyword scorer will still retrieve the `category_vocabulary` chunk because
  "pharmacy" overlaps with tokens in the document text. Less precise than real
  embeddings, but functional with no embedding API dependency.

---

## Exercise 2: MCP Client Agent (`02_langgraph_agent.ts`)

**Motivating question**: "Once you have an MCP server, what does a client that
actually _reasons_ look like — versus one that just calls tools blindly?"

Exercise 1 built the server. This exercise builds the **client**: a TypeScript
program that starts an `@modelcontextprotocol/sdk` `Client`, connects to
`01_mcp_server.ts` over stdio, and runs an agentic loop where Claude decides
which tools to call, in what order, and whether to retry.

### Architecture

The agent process (`02_langgraph_agent.ts`) and the server process
(`01_mcp_server.ts`) are separate, communicating over stdin/stdout. The client
never imports the server — it only knows what the server advertises via the
`tools/list` response.

### The Agent Loop

The agent loop calls the Claude API with the dynamically-loaded MCP tools, checks
the `stop_reason`, and for each `tool_use` block in the response calls
`mcpClient.callTool(block.name, block.input)` and feeds the result back as a
tool result message. The loop continues until `stop_reason === "end_turn"`.
`mcpTools` is built dynamically from `client.listTools` — Claude learns what
tools exist at runtime, the same way Claude Desktop does.

### What It Demonstrates

| Behaviour            | How it appears in the trace                                                          |
| -------------------- | ------------------------------------------------------------------------------------ |
| **Discovery**        | Agent calls `list_datasets` before any query — it doesn't assume what data exists    |
| **Schema lookup**    | Agent calls `explain_schema` before writing SQL — avoids column name errors          |
| **Retry on error**   | If `query_places` returns malformed SQL, agent re-calls `explain_schema` and retries |
| **Self-termination** | Agent stops when it has a complete SQL answer, not after a fixed number of steps     |

### Running

Start the agent with `npx tsx src/exercises/agentic-gis/02_langgraph_agent.ts --query "coffee shops within 500m of Dolores Park"` — it spawns the MCP server automatically. Set `ANTHROPIC_API_KEY` in `.env.local` at the project root.

The exercise files are at `src/exercises/agentic-gis/`: `01_mcp_server.ts` (Exercise 1, complete) and `02_langgraph_agent.ts` (Exercise 2).

### What to Observe — Exercise 2

- **The `tools/list` call happens first**: Before Claude sends a single message,
  the client calls `list_tools`. Compare the latency of this round-trip vs. the
  approach where tool schemas were hardcoded in the API call.

- **Reasoning trace**: The agent produces the same kind of step-by-step
  trace as the observability exercise in Agentic Geo Queries — but the tool calls
  now go through the MCP protocol layer. The reasoning is identical; the interface
  is portable.

- **Self-correction in action**: Try a query with an unusual category (e.g.,
  "urgent care clinics"). Watch the agent call `explain_schema`, find the
  `category_vocabulary` chunk, and adjust the SQL it generates.

- **Client/server decoupling**: The agent file contains zero knowledge of how
  `query_places` works internally. Swap the server implementation (different
  dataset, different LLM, different SQL dialect) and the client code is
  unchanged. This is the portability payoff.

## Practical Exercises


