/**
 * Exercise 02: Browser-Side SQL Agent — Web Worker Agentic Loop
 * ==============================================================
 * NL-to-SQL Web GIS, Exercise 2
 *
 * This file is a heavily-annotated conceptual skeleton.
 * It's not runnable, but it explains the design for moving the agentic
 * loop from the server in the Agentic GIS module into the browser using a Web Worker.
 *
 * ==========================================================================
 * BACKGROUND: Server loop vs. Browser loop trade-offs
 * ==========================================================================
 *
 * The Agentic GIS module runs the agent loop on the server. The browser sends a POST
 * request to /api/scout/agent-query, the server runs several turns, and 
 * then sends the final response back.
 *
 * This has a specific latency profile:
 *   - The user has to wait for all turns to finish before they see anything.
 *   - Each turn takes about 200-500ms for the server to talk to Anthropic.
 *   - A 3-turn loop means about 1-2 seconds of "black-box" waiting for the user.
 *
 * This implementation (the "Lab" pattern) suggests a browser-side agent instead. In this 
 * model, the browser uses a Web Worker to call the Anthropic API directly 
 * and execute DuckDB-Wasm locally.
 *
 * Trade-offs:
 *
 *   Server-side loop (Agentic GIS):
 *   - Pro: The API key stays safely on the server.
 *   - Pro: The client code remains simple.
 *   - Con: There's a full round-trip for every turn.
 *   - Con: You can't stream information to the user.
 *   - Con: The user doesn't see anything until the whole process is done.
 *
 *   Browser-side loop (this exercise):
 *   - Con: The API key has to be in the browser (usually done via BYOK).
 *   - Pro: You can stream tokens and tool calls to the UI in real time.
 *   - Pro: DuckDB-Wasm executes in the same process.
 *   - Pro: You don't need any extra API routes.
 *   - Pro: Each tool call is visible to the user as it happens.
 *
 * WHEN to use each:
 *   Server-side: Admin-keyed deployments, simple apps, no streaming needed
 *   Browser-side: BYOK products (Felt, Observable, Hex), streaming UX, demos
 *
 * ==========================================================================
 * ARCHITECTURE: Web Worker for the agentic loop
 * ==========================================================================
 *
 * Why use a Web Worker?
 *   - The agent loop involves waiting for network requests, and running it
 *     on the main thread would block React's rendering.
 *   - Web Workers run in a separate thread, which prevents UI lag.
 *   - Workers can use fetch() for API calls. 
 *   - While they can't touch the DOM, they can easily pass data back to 
 *     the main thread.
 *
 * Message protocol:
 *   Main to Worker:   Sending the query and the API key.
 *   Worker to Main:   Sending tool call details, the final SQL and config, 
 *                     or any errors that occur.
 */

// ---------------------------------------------------------------------------
// Worker skeleton (would live in public/workers/agent.worker.ts or similar)
// ---------------------------------------------------------------------------

// NOTE: This is pseudocode — Web Workers use postMessage, not import/export.
// A real implementation would use the Worker constructor with module type.

type AgentWorkerMessage =
  | { type: 'start'; query: string; apiKey: string }
  | { type: 'tool_result'; tool_use_id: string; result: string };

type AgentWorkerResponse =
  | { type: 'tool_call'; step: number; tool: string; input: Record<string, unknown> }
  | { type: 'sql_ready'; sql: string; layer_config: Record<string, unknown>; reasoning: string }
  | { type: 'stream_token'; text: string }
  | { type: 'error'; message: string };

declare function postMessage(msg: AgentWorkerResponse): void;

/**
 * Simplified worker message handler.
 * In practice this would be in a dedicated file loaded via:
 *   new Worker(new URL('./agent.worker.ts', import.meta.url))
 */
async function handleWorkerMessage(msg: AgentWorkerMessage) {
  if (msg.type !== 'start') return;

  const { query, apiKey } = msg;

  // The worker calls the Anthropic API directly using the BYOK key.
  // This only works in BYOK mode — the API key must be the user's own.
  const anthropicEndpoint = 'https://api.anthropic.com/v1/messages';

  const tools = [
    {
      name: 'execute_sql',
      description: 'Execute DuckDB SQL. Returns a sentinel — the main thread executes it.',
      input_schema: {
        type: 'object',
        properties: { sql: { type: 'string' } },
        required: ['sql'],
      },
    },
    {
      name: 'return_visualization',
      description: 'Return final SQL + visualization config.',
      input_schema: {
        type: 'object',
        properties: {
          sql: { type: 'string' },
          layer_config: {
            type: 'object',
            properties: {
              type: { type: 'string', enum: ['circle', 'heatmap'] },
              color: { type: 'array', items: { type: 'number' }, minItems: 3, maxItems: 3 },
              radius: { type: 'number' },
              opacity: { type: 'number' },
            },
            required: ['type', 'color', 'radius', 'opacity'],
          },
          reasoning: { type: 'string' },
        },
        required: ['sql', 'layer_config', 'reasoning'],
      },
    },
  ];

  const messages: Array<{ role: string; content: unknown }> = [
    { role: 'user', content: query },
  ];

  for (let turn = 0; turn < 8; turn++) {
    // Call Anthropic API from the worker — using streaming for token-by-token UX
    const response = await fetch(anthropicEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: 'claude-sonnet-4-6',
        max_tokens: 2048,
        tools,
        messages,
        // stream: true  ← uncomment to enable streaming tokens to the UI
      }),
    });

    const data = await response.json();

    if (data.stop_reason === 'end_turn') break;
    if (data.stop_reason !== 'tool_use') break;

    messages.push({ role: 'assistant', content: data.content });

    const toolResults: Array<{ type: string; tool_use_id: string; content: string }> = [];

    for (const block of data.content) {
      if (block.type !== 'tool_use') continue;

      postMessage({
        type: 'tool_call',
        step: turn + 1,
        tool: block.name,
        input: block.input,
      });

      if (block.name === 'return_visualization') {
        // Terminal action — signal the main thread
        postMessage({
          type: 'sql_ready',
          sql: block.input.sql,
          layer_config: block.input.layer_config,
          reasoning: block.input.reasoning,
        });
        return;
      }

      if (block.name === 'execute_sql') {
        // Since the worker can't run DuckDB-Wasm directly (it's in the main 
        // thread), we have to send the SQL to the main thread and wait for 
        // it to finish executing.
        //
        // A full implementation would use an async postMessage round-trip:
        //   1. Worker sends the SQL request.
        //   2. Main thread runs DuckDB-Wasm and sends back the result.
        //   3. Worker receives the result and continues its loop.
        //
        // In this exercise skeleton, we'll just mock the result.
        const mockResult = JSON.stringify({
          note: 'SQL executed by main thread DuckDB-Wasm',
          row_count: 42,
        });
        toolResults.push({
          type: 'tool_result',
          tool_use_id: block.id,
          content: mockResult,
        });
      }
    }

    messages.push({ role: 'user', content: toolResults });
  }

  postMessage({ type: 'error', message: 'Agent completed without calling return_visualization' });
}

// ---------------------------------------------------------------------------
// Main thread — how you'd use the worker in a React component
// ---------------------------------------------------------------------------

/**
 * Example React hook for the browser-side agent loop.
 * This is pseudocode — the actual Worker path setup differs by bundler.
 */
function useBrowserAgent() {
  // In a real component:
  //
  // const workerRef = useRef<Worker | null>(null);
  //
  // useEffect(() => {
  //   workerRef.current = new Worker(
  //     new URL('./agent.worker.ts', import.meta.url),
  //     { type: 'module' }
  //   );
  //
  //   workerRef.current.onmessage = (e: MessageEvent<AgentWorkerResponse>) => {
  //     switch (e.data.type) {
  //       case 'tool_call':
  //         // Show reasoning trace in real time
  //         setTrace(prev => [...prev, e.data]);
  //         break;
  //       case 'sql_ready':
  //         // Execute SQL in DuckDB-Wasm (main thread), update map
  //         executeQuery(e.data.sql).then(({ count }) => setResultCount(count));
  //         setLayerConfig(e.data.layer_config);
  //         setReasoning(e.data.reasoning);
  //         break;
  //       case 'error':
  //         setError(e.data.message);
  //         break;
  //     }
  //   };
  //
  //   return () => workerRef.current?.terminate();
  // }, []);
  //
  // const fireQuery = (query: string, apiKey: string) => {
  //   workerRef.current?.postMessage({ type: 'start', query, apiKey });
  // };
}

// ---------------------------------------------------------------------------
// TODO: Implement the worker message handler
// ---------------------------------------------------------------------------
//
// TODO 1: Create a real Web Worker file at:
//   src/workers/agent.worker.ts
//
// Implement the message handler that:
//   a) Receives { type: 'start', query, apiKey }
//   b) Calls the Anthropic API with the tools defined above
//   c) For execute_sql tool calls: posts { type: 'execute_sql_request', sql, tool_use_id }
//      to the main thread and AWAITS the result before continuing
//   d) For return_visualization: posts { type: 'sql_ready', ... }
//
// TODO 2: In the main thread (LabMapPanel or a new BrowserAgentPanel):
//   - Create the Worker on mount
//   - Listen for 'execute_sql_request' messages and execute via DuckDB-Wasm
//   - Post the result back: { type: 'tool_result', tool_use_id, result }
//   - Handle 'sql_ready' to update the map and LayerConfigInspector
//
// TODO 3: Compare latency:
//   - Server loop (Agentic GIS agent-query): time from submit to first map render
//   - Browser loop (this exercise): does real-time streaming make it feel faster
//     even if total time is similar?

// ---------------------------------------------------------------------------
// Live implementation references
// ---------------------------------------------------------------------------
//
// Current Scout Lab page (uses server-side loops):
//   src/app/scout/lab/page.tsx
//
//   Agentic GIS server-side agent loop (the pattern to move to the browser):
//   src/app/api/scout/agent-query/route.ts
//
// The Agentic GIS MCP agent (async multi-step pattern reference):
//   src/exercises/agentic-gis/02_langgraph_agent.ts

// Suppress "unused" warnings on the exercise functions above
export { handleWorkerMessage, useBrowserAgent };
