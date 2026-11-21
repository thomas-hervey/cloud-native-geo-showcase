/**
 * Exercise 01: Generative UI — Structured LLM → MapLibre Layer
 * ==============================================================
 * NL-to-SQL Web GIS, Exercise 1
 *
 * This file is a heavily-annotated reference implementation.
 * It's not meant to be run on its own; instead, it explains the patterns used in:
 *   src/app/scout/lab/components/LabMapPanel.tsx
 *   src/app/api/scout/generative-query/route.ts
 *
 * ==========================================================================
 * BACKGROUND: Why structured output over free-text SQL?
 * ==========================================================================
 *
 * In the Agentic GIS module (agent-query), the LLM returns a plain SQL string in text.
 * The server extracts it with a regex and hands it to the browser.
 *
 * This works fine for data retrieval, but it leaves the rendering decision
 * entirely to the client, which usually results in hardcoded red markers.
 * This approach often misses the "intent" of the AI. For instance, is this meant 
 * to be a density pattern, a specific category, or a highlight?
 *
 * This implementation extends that with GENERATIVE UI:
 *   The LLM returns BOTH the data query AND the visual encoding spec.
 *   "Show me green parks" → SQL for parks + color: [34, 197, 94]
 *   "Density of coffee shops" → SQL for coffee shops + type: 'heatmap'
 *
 * The key insight: the map IS the answer. Visual encoding is part of
 * the response, not an afterthought.
 *
 * WHY STRUCTURED OUTPUT (tool use) OVER FREE-TEXT JSON?
 * -------------------------------------------------------
 * Option A (free-text): You might ask the AI to "return JSON with this shape..." 
 * in the system prompt.
 *
 * Problems:
 *   - The AI might include markdown fences, extra explanation text, or small 
 *     format variations that break the parser.
 *   - Parsing is fragile. A single missing comma can break the whole response.
 *   - There isn't any schema enforcement at the API level.
 *
 * Option B (tool use): Define a tool with a JSON schema that the AI is required to call.
 *
 * Benefits:
 *   - The Anthropic API enforces the schema, so you always get well-typed input.
 *   - Required fields are always present.
 *   - Enums prevent hallucinated types like "scatter" instead of "circle".
 *   - You can use minimum and maximum constraints for things like radius and opacity.
 *
 * The return_visualization tool in this module is a good example of using 
 * tool-calling as a way to get a structured response instead of just calling 
 * an external API.
 */

// ---------------------------------------------------------------------------
// Annotated LayerConfig type
// ---------------------------------------------------------------------------

/**
 * LayerConfig — the visualization specification the LLM generates.
 *
 * Each field was chosen to map directly to MapLibre paint properties
 * (see src/lib/scout-layer-config.ts for the conversion functions):
 *
 *   type:    'circle' for discrete points, 'heatmap' for density patterns
 *            The LLM is instructed to choose 'heatmap' when the query mentions
 *            "density", "concentration", "where are most", etc.
 *
 *   color:   [R, G, B] triplet 0-255. The LLM uses semantic color mapping:
 *            parks → green, restaurants → orange, water → blue, hospitals → red
 *            Being explicit about the range (not 0-1 floats) avoids ambiguity.
 *
 *   radius:  6-12 pixels. Larger for sparse data (hospitals: 10),
 *            smaller for dense data (coffee shops: 6-7).
 *
 *   opacity: 0.7-0.9. Lower for dense overlapping data.
 *
 *   label:   Human-readable description of the style choice, e.g.
 *            "warm orange — restaurants". Shown in LayerConfigInspector.
 */
interface LayerConfig {
  /** 'circle' for discrete points, or 'heatmap' for density patterns. */
  type: 'circle' | 'heatmap';
  /** [R, G, B] triplet between 0-255. */
  color: [number, number, number];
  /** Radius in pixels, typically between 6 and 12. */
  radius: number;
  /** Opacity between 0 and 1. */
  opacity: number;
  /** A short description of why these style choices were made. */
  label?: string;
}

// ---------------------------------------------------------------------------
// Simplified LabMapPanel flow (annotated)
// ---------------------------------------------------------------------------
//
// The actual implementation is in:
//   src/app/scout/lab/components/LabMapPanel.tsx
//
// This skeleton shows the conceptual flow with comments.

type QueryResult = { count: number };

export async function sampleGenerativeQueryFlow(
  userQuery: string,
  executeQuery: (sql: string) => Promise<QueryResult>
): Promise<void> {
  // Step 1: Call the generative-query API endpoint.
  // This runs the agentic loop on the server and returns both SQL and LayerConfig.
  const response = await fetch('/api/scout/generative-query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: userQuery }),
  });

  const data: {
    sql: string;
    layer_config: LayerConfig;
    viewport?: { longitude: number; latitude: number; zoom: number };
    reasoning: string;
    reasoning_trace: Array<{ step: number; tool: string; input: unknown; output: string; elapsed_ms: number }>;
    provider: string;
  } = await response.json();

  // Step 2: Validate the layer_config. The server already clamps values,
  // but a defensive check here prevents rendering crashes.
  const layerConfig: LayerConfig = data.layer_config;
  // (In production code, also verify color[].length === 3, type is valid, etc.)

  // Step 3: Execute the SQL in DuckDB-Wasm (browser-side).
  // The parent passes `executeQuery` as a callback from LabMap's onReady.
  const { count } = await executeQuery(data.sql);

  // Step 4: Display results.
  // - LabMap re-renders with the new layerConfig prop → MapLibre setPaintProperty
  // - LayerConfigInspector shows the color swatch, label, and reasoning
  console.log(`Found ${count} results. Style: ${layerConfig.type} in rgb(${layerConfig.color.join(',')})`);
  console.log('LLM reasoning:', data.reasoning);
}

// ---------------------------------------------------------------------------
// TODO Exercise A: Modify the system prompt for heatmap on density queries
// ---------------------------------------------------------------------------
//
// Currently the system prompt at src/app/api/scout/generative-query/route.ts says:
//   "type: 'circle' for point data, 'heatmap' for density queries"
//
// The LLM uses keyword matching to decide, but it can be inconsistent.
//
// TODO: Update the system prompt to be more explicit. Add a rule:
//   "If the query contains 'density', 'concentration', 'hotspot', 'cluster',
//    or 'most X per area', always choose type='heatmap'."
//
// Then test with: "Show me the density of coffee shops in SF"
// Expected: layer_config.type === 'heatmap'
//
// Hint: You can find the prompt in buildSystemPrompt() at:
//   src/app/api/scout/generative-query/route.ts

// ---------------------------------------------------------------------------
// TODO Exercise B: Add stroke_color field to LayerConfig
// ---------------------------------------------------------------------------
//
// The circle paint currently uses a hardcoded white stroke:
//   'circle-stroke-color': '#ffffff'
//
// TODO 1: Add `stroke_color?: [number, number, number]` to LayerConfig in:
//   src/lib/scout-types.ts
//
// TODO 2: Update toCirclePaint() in src/lib/scout-layer-config.ts:
//   'circle-stroke-color': cfg.stroke_color
//     ? `rgb(${cfg.stroke_color.join(', ')})`
//     : '#ffffff',
//
// TODO 3: Add `stroke_color` to the `return_visualization` tool schema in:
//   src/app/api/scout/generative-query/route.ts
//   (Add it as an optional field inside layer_config.properties)
//
// TODO 4: Update the system prompt to instruct the LLM:
//   "Use stroke_color to add contrast: dark data on light basemap → white stroke,
//    light data on dark areas → dark stroke."
//
// After these changes, try: "Show me hospitals" — the LLM should choose
// a red fill with a dark red stroke for extra visibility.

// ---------------------------------------------------------------------------
// Live implementation reference
// ---------------------------------------------------------------------------
//
// LabMapPanel.tsx:  src/app/scout/lab/components/LabMapPanel.tsx
// LabMap.tsx:       src/app/scout/lab/components/LabMap.tsx
// API route:        src/app/api/scout/generative-query/route.ts
// Type definitions: src/lib/scout-types.ts
// Paint converters: src/lib/scout-layer-config.ts

export {};
