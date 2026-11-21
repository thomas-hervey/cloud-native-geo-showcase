> **Live App & Exercise Access**: Interactive tools in this track (such as the
> live **Scout** interface or spatial evaluation tools) are **not yet public**.
> If you would like to test these applications, please **reach out to the
> author**.

## Overview

Phase 3 assembles the full Scout web application — the Next.js frontend that wires together the Phase 2 translation pipeline, a MapLibre GL JS basemap, and DuckDB-Wasm for in-browser query execution. When a user submits a natural language question, the `ChatBar` component posts to the Phase 2 API route, receives SQL back, passes it to `ScoutMap`, which executes the query against the GeoParquet file on S3 and renders the results as map markers — all without a server-side query engine.

## Key Concepts

### 1. The Thick-Client Architecture

Scout's entire query lifecycle after the LLM call runs in the browser. DuckDB-Wasm executes SQL against GeoParquet files hosted on S3 using HTTP range requests via the `httpfs` extension, and MapLibre GL JS renders the results. The only server-side infrastructure is the Next.js API route that calls the LLM — the database, the query engine, and the map renderer are all client-side. This eliminates backend compute costs and latency for every operation except the initial LLM translation.

### 2. Component Architecture: ChatBar → Page → ScoutMap

Scout's frontend uses three components in sequence. `ChatBar` is a controlled input that submits queries to the Phase 2 API route and receives `{ sql, provider }` back. `page.tsx` holds the shared state and wires callbacks between components. `ScoutMap` manages two long-lived objects initialized on mount: the MapLibre basemap and the DuckDB-Wasm instance. When SQL arrives from `ChatBar`, `ScoutMap` executes it against the GeoParquet file, converts rows to markers, and updates the map.

### 3. HTML Markers vs. WebGL Layers

For datasets under 5,000 points, MapLibre `Marker` objects (DOM elements) provide the simplest implementation for hover and popup handling. Each marker is a separate DOM node, which is manageable at small scale but degrades for larger datasets. For 100k+ points, WebGL layers (GeoJSON source + paint layer) are required — they move geometry management into MapLibre's rendering pipeline and support `setPaintProperty` updates without DOM manipulation. The choice is a product decision driven by expected result set size.

## 1. The Query Lifecycle

Tracing a single user query from keystroke to rendered pixels reveals the
distributed nature of the application. The user types a question, `ChatBar`
posts it to the Phase 2 API route, the LLM returns a SQL statement, and
`ChatBar` passes it to `ScoutMap` via a callback. `ScoutMap` executes the SQL
against the GeoParquet file on S3 using DuckDB-Wasm's `httpfs` extension — only
fetching the byte ranges it needs — converts the result to map markers, and
renders them on the MapLibre basemap.

The network only touches two endpoints: the Scout API route (tiny JSON request)
and the GeoParquet file (partial byte-range fetch via `httpfs`). Everything
else, including SQL execution, geometry evaluation, and rendering, happens
locally in the browser.

## 2. Product Patterns in Client-Side GIS

The frontend architecture is where the "thick client" strategy is validated:

- **The map is the interface**: In traditional BI tools, a map is often an
  optional visualization. In geospatial products, the map _is_ the primary
  output — every result and filter is inherently spatial.
- **DuckDB-Wasm initialization is a UX priority**: The Wasm binary takes 1–3
  seconds to load on the first visit. Handling this with a clear loading state
  or progress indicator is a requirement: "The app must maintain a clear status
  while the query engine initializes."
- **Open Source Map Engines**: MapLibre GL JS is the open-source fork of Mapbox,
  offering high performance without requiring a token for development. It
  remains compatible with free tile providers like Stadia Maps.
- **HTML Markers vs. WebGL Layers**: For datasets under 5,000 points, MapLibre
  `Marker` objects (DOM elements) provide the simplest implementation for
  handling hover and popups. Larger datasets (100k+ points) eventually require
  WebGL layers to trade simple DOM management for GPU-scale performance.

## 3. Component Architecture

Scout's frontend consists of three components working in sequence:

`ScoutMap.tsx` manages two long-lived objects initialized on mount: the MapLibre
basemap (background tiles, zoom, projection) and the DuckDB-Wasm instance
(spatial and httpfs extensions). When a SQL string is received from the
`ChatBar`, the component executes the query, converts the rows to markers, and
updates the map display.

`ChatBar.tsx` is a controlled input component that handles query submission: it
triggers a loading state, posts the query to `/api/scout/query`, receives the
generated SQL and provider metadata, passes the SQL to the map component via a
callback, and displays which provider generated the response.

`page.tsx` wires the components together using shared callbacks and displays the
current SQL for transparency and debugging.

## Practical Exercises


