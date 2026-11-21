> [!TIP]
> **Try it out!** You can explore the interactive version of the capstone project on the
> [Scout Lab](/scout/lab). **NOTE: This feature is currently gated.**

> **Live App & Exercise Access**: Interactive tools in this track (such as the
> live **Scout** interface or spatial evaluation tools) are **not yet public**.
> If you would like to test these applications, please **reach out to the
> author**.

## Overview

Scout is the capstone project of this curriculum — a "Chat-to-Map" application that combines STAC, DuckDB, and LLMs to answer natural language geospatial queries and render results on an interactive map. It is assembled across three phases: data ingestion (Phase 1), the LLM translation backend (Phase 2), and the full web application (Phase 3). Each phase builds directly on the last, producing a working end-to-end system by the final module.

## Key Concepts

### 1. The Scout Architecture

Scout is structured as three sequential phases: Phase 1 builds the ETL pipeline that fetches Overture Maps data, filters it to San Francisco, and writes a spatially-optimized GeoParquet file alongside a STAC catalog. Phase 2 builds the API route that converts a natural language query into executable DuckDB SQL using an LLM. Phase 3 assembles the Next.js frontend with MapLibre GL JS and DuckDB-Wasm to render results in the browser.

### 2. Chat-to-Map: How a Question Becomes a Layer

When a user types "show me coffee shops near Dolores Park," the Scout API route injects the STAC catalog (schema + closed category vocabulary) into a system prompt, calls an LLM to generate a DuckDB SQL statement, and returns that SQL to the browser. DuckDB-Wasm then executes the query directly against the GeoParquet file hosted on S3 using HTTP range requests, and MapLibre renders the results as point markers — no server-side query engine required.

### 3. The Role of Each Key Technology

STAC provides the data contract: a machine-readable catalog that describes the schema, bounding box, and category vocabulary so the LLM can generate accurate SQL without hallucinating column names. DuckDB-Wasm moves query execution into the browser, eliminating any always-on backend database. The LLM (Anthropic Claude or OpenAI GPT-4o, swappable via an environment variable) handles natural language understanding and SQL generation.

## 1. The Goal

> **User:** "Show me all coffee shops in San Francisco within 500 metres of a
> park."

**Scout** will:

1. **Understand** the intent using an LLM.
2. **Translate** natural language into a spatial SQL query.
3. **Execute** that query directly in the browser using DuckDB-Wasm.
4. **Visualize** the results on an interactive map instantly.

![Scout App](/assets/cng-tutorial-scout-app.png)

## 2. Why This Matters for Product Patterns

The Scout lab embodies three forces reshaping the geospatial product landscape:

- **Zero backend cost**: The only infrastructure is a static file host (S3/R2).
  No always-on database server, no tile server, and no compute bill that grows
  with your user count.
- **Latency-free UX**: Once data is cached in the browser, every filter and
  query runs on the user's own CPU. No network round-trip means interactions
  feel instant. This is a quantifiable product differentiator: interactions
  under 100ms are perceived as immediate.
- **Natural language as the interface**: Hiding SQL behind a chat bar makes
  complex geospatial analysis accessible to non-technical stakeholders. This
  pattern powers Felt AI, Esri's ArcGIS Instant Apps, and Google Maps'
  conversational search.
- **Auditable queries**: Because the output is a standard SQL string, every
  query is inspectable, loggable, and reproducible. This level of transparency
  is essential for compliance and data governance.

## 3. The Stack

| Layer            | Technology                        |
| ---------------- | --------------------------------- |
| Framework        | Next.js 15 (App Router)           |
| Styling          | Tailwind CSS 4                    |
| Basemap          | MapLibre GL JS                    |
| Data overlay     | Deck.gl: GeoJsonLayer             |
| Browser database | DuckDB-Wasm (httpfs + spatial)    |
| ETL              | DuckDB Python                     |
| Data source      | Overture Maps (S3, 2024 release)  |
| LLM (swappable)  | Anthropic Claude or OpenAI GPT-4o |

## 4. Next Steps

The project continues through three more modules, each one building directly on
the last:

- **Data Sourcing & ETL**: Query Overture Maps on S3, filter to San Francisco,
  write spatially-optimized GeoParquet, and generate a STAC catalog describing
  the output.
- **Semantic Translation Backend**: Write the Next.js API route that converts a
  user's question into a valid DuckDB SQL string using a swappable LLM.
- **Web App Assembly**: Integrate the final Scout UI with MapLibre GL JS,
  DuckDB-Wasm, and Deck.gl for the "Chat-to-Map" experience.

## Practical Exercises

Scout Intro is the architecture and design module — the exercises live in each subsequent phase. Reading through the stack table and the architecture diagrams here gives you the mental model you will need to work through Phases 1–3.

*Exercise files coming soon.*
