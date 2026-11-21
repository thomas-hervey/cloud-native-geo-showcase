---
title: "Prototyping NL-to-SQL Web GIS (Felt Style)"
---

## Overview

This prototype builds a natural-language-to-SQL web application for geospatial data — users type plain English questions and get maps and data back from a DuckDB spatial backend, with the map styled automatically by the LLM. It extends Scout's translation pipeline by adding a `return_visualization` tool that constrains the LLM to return both a SQL query and a MapLibre layer configuration (type, color, radius, opacity) in a single structured response — so "show me parks" yields green polygons and "coffee shop density" yields a heatmap.

## Key Concepts

### 1. NL-to-SQL Pipeline with Generative UI

The naive approach returns SQL and renders everything as hardcoded red dots. This module makes visual encoding part of the AI response: the LLM generates application state (layer configuration), not just data. A `return_visualization` tool with a JSON schema constrains the model's output to valid MapLibre paint properties, eliminating free-text JSON parsing errors and hallucinated field names. The result is "generative UI" — each query produces a semantically appropriate map style.

### 2. DuckDB-Wasm as the Spatial Backend

All query execution happens in the browser via DuckDB-Wasm. The `httpfs` extension fetches only the byte ranges of the GeoParquet file needed to answer each query, and the `spatial` extension provides ST_* functions for proximity and geometry operations. There is no server-side query engine — the only server component is the Next.js API route that calls the LLM. This means zero backend compute cost and no latency after the initial Wasm initialization.

### 3. MapLibre GL Layers vs. HTML Markers

Scout Phase 3 used HTML markers — one DOM node per result, requiring full removal and re-insertion on style changes. This module uses the proper MapLibre approach: a GeoJSON source added once, with circle or heatmap layers referencing it. When the LLM returns a new `layer_config`, a single `setPaintProperty` call updates the visual in place — no DOM manipulation, no marker removal. This pattern scales to much larger result sets and supports zoom-dependent rendering behavior that HTML markers cannot provide.

---

## What Problem Does This Solve?

In the previous Scout modules, Scout returns SQL that gets rendered as hardcoded
red dots. The user has no visual signal about what the data represents. For
example, parks look the same as hospitals look the same as restaurants. Color,
symbol choice, and density representation are afterthoughts.

NL-to-SQL tools, such as Felt's AI tools (style pop-ups, custom extensions,
etc.), solve this by making visual encoding a part of the AI response. For
example, an effective use of this tool would be to ask "show me parks" and get
_green_ polygons. When you ask "coffee shop density", you get a heatmap.
The map IS the answer, not just a container for results.

This is **generative UI**. The LLM generates application state (layer
configuration), not just data.

---

## Architecture

The user query goes to `POST /api/scout/generative-query`. An agent loop calls
two tools: `execute_sql` (which returns the data) and `return_visualization`
(which returns both the SQL and the layer config). The `LabMapPanel` component
receives the structured result, executes the SQL against DuckDB-Wasm, and calls
`map.setLayerConfig` on the MapLibre instance — all in the browser.

---

## Key Concept: Structured Output via Tool Use

The naive approach: ask the LLM to "return JSON with this shape" in the system
prompt.

**Problems with free-text JSON:**

- The LLM may wrap the response in markdown code fences
- A missing comma or trailing `}` breaks `JSON.parse`
- No schema enforcement — hallucinated field names silently pass through

**The tool-use approach:** Define a `return_visualization` tool with a JSON
schema. The Anthropic API enforces the schema before the response reaches your
code. The schema constrains `type` to `'circle'` or `'heatmap'` via an enum,
`color` to exactly 3 numbers via `minItems`/`maxItems`, and `radius` to a
3–20 range via `minimum`/`maximum`. The server still validates and clamps
(defense in depth), but the schema dramatically reduces bad inputs.

This is the same technique used to build "function calling" workflows — it's
just applied here to enforce a response shape rather than call an external API.

---

## Key Concept: MapLibre Layers vs HTML Markers

Scout Phase 3 used HTML markers for rendering. Each marker is a separate DOM
element — 500 markers = 500 DOM nodes. You can't update style without removing
and re-adding all markers. Popups require per-marker event listeners. They don't
participate in MapLibre's rendering pipeline (no zoom-dependent scaling).

This module uses the **proper MapLibre approach**: a GeoJSON source added once
plus a layer that references it. When `layerConfig` changes, `setPaintProperty`
updates the visual in place — no re-render needed. Popups use a single event
listener on the layer, not per-marker listeners. This makes generative UI
practical: when the LLM returns a different `layer_config`, one API call updates
the map style without touching the DOM.

---

## The Scout Lab

Navigate to `/scout/lab` to see the side-by-side comparison interface.

The left panel runs one of the existing Scout modes (stuffing, RAG, or agent)
and renders with fixed blue styling — just like the existing `/scout` page.

The right panel calls `/api/scout/generative-query` and renders with the
`LayerConfig` the LLM returned. The **LayerConfigInspector** panel shows a
color swatch, the LLM's `reasoning` for its style choices, and the raw
`layer_config` JSON.

**Unified** (default): A single `LabPromptBar` at the bottom fires both panels
simultaneously. Useful for comparing the same query across both approaches.

**Split**: Each panel has its own prompt bar. Useful for testing different
queries independently.

The left panel shows a small `→ agent` button that cycles through stuffing → RAG
→ agent, letting you compare all four Scout approaches on the same query.

---

## Exercises

### Exercise 1: `01_generative_ui.tsx` — Structured LLM → MapLibre Layer

Reference file: `src/exercises/31-nl-sql-web/01_generative_ui.tsx`

This annotated file explains why structured output (tool use) is preferred over
free-text JSON prompting, the design of the `LayerConfig` type and why each
field maps to a MapLibre property, and the flow from user query → API → DuckDB-Wasm
→ map render.

**TODO A:** Modify the system prompt in
`src/app/api/scout/generative-query/route.ts` to be more explicit about when to
use `'heatmap'`. Add a rule: if the query mentions "density", "concentration",
or "hotspot", always choose `type: 'heatmap'`. Test with: _"Show me the density
of coffee shops in SF"_.

**TODO B:** Add a `stroke_color` field to `LayerConfig` and update
`toCirclePaint()` to use it. Update the tool schema and system prompt
accordingly. Test with: _"Show me hospitals"_ — expect a red fill with a dark
border.

### Exercise 2: `02_browser_sql_agent.tsx` — Full Browser-Side Agent

Reference file: `src/exercises/31-nl-sql-web/02_browser_sql_agent.tsx`

This annotated file explains the server vs. browser agent trade-off and sketches
the Web Worker architecture for moving the agentic loop client-side.

**TODO:** Implement the Web Worker (`src/workers/agent.worker.ts`) that receives
`{ type: 'start', query, apiKey }` from the main thread, calls the Anthropic
API directly using the BYOK key, for `execute_sql` tool calls posts the SQL to
the main thread for DuckDB-Wasm execution and awaits the result, and for
`return_visualization` posts the final result and terminates. This eliminates
the server round-trip for the agentic loop entirely.

---

## What to Observe

### Prompts to try in Scout Lab

| Query               | Expected left (agent) | Expected right (generative) |
| ------------------- | --------------------- | --------------------------- |
| Show me all parks   | Blue dots             | Green circles               |
| Find restaurants    | Blue dots             | Orange circles              |
| Coffee shop density | Blue dots             | Heatmap (warm tones)        |
| Show me hospitals   | Blue dots             | Red circles, larger radius  |
| Breweries in SF     | Blue dots             | Amber/yellow circles        |

### Failure modes to look for

1. **Inconsistent color choices:** Ask for parks twice in separate queries. Does
   the LLM always choose green, or does it vary? (Semantic consistency is not
   guaranteed.)

2. **Heatmap vs circle confusion:** Try "show me where most coffee shops are" —
   does the LLM choose heatmap (density signal) or circle (discrete features)?
   The current prompt leaves this ambiguous.

3. **Invalid color values:** Check the raw JSON in LayerConfigInspector.
   Occasionally the LLM returns floats (0.5, 0.8) instead of 0-255 integers. The
   server clamps these, so the map won't crash — but the color will be
   near-black.

4. **Viewport mismatches:** The generative-query route accepts a `bbox`
   parameter but the Lab page doesn't pass it yet. This means the LLM has no
   viewport context, so proximity queries like "near Dolores Park" rely entirely
   on the SQL the LLM writes.

---

## Going Further

**Deck.gl aggregation layers:** MapLibre's heatmap layer is a simple density
kernel. For real aggregation — hexbin, grid, or cluster visualizations —
Deck.gl's `HexagonLayer`, `GridLayer`, and `ScatterplotLayer` offer more
expressive semantics. The `LayerConfig` type would need a `deck_gl_layer_type`
field and a separate paint converter.

**Multi-layer responses:** The current `return_visualization` tool returns a
single layer config. A more advanced version would return an array of layers —
e.g., a heatmap of restaurants PLUS circle markers for the top 10. This requires
the LLM to reason about layer ordering (z-index).

**Streaming the agent trace:** Both panels currently show the reasoning trace
after the full response arrives. Using the Anthropic streaming API (and a Web
Worker per Exercise 2), you could show each tool call as it happens — making the
"thinking" process visible to the user in real time.

## Practical Exercises


