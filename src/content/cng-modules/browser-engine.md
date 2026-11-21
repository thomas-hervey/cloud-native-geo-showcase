## Overview

Running geospatial compute in the browser — via DuckDB-Wasm — eliminates the backend entirely for a class of analytical map products. Instead of a server querying a database and returning results, the browser downloads a compressed Parquet file directly from cloud storage and runs SQL against it locally. Every filter, join, and spatial predicate executes in milliseconds against in-memory data, making the map feel instantaneous and removing always-on server costs.

## Key Concepts

### 1. The Frontend Database Pattern

DuckDB-Wasm brings the full DuckDB SQL engine — including the spatial extension (GEOS geometry operations; full PROJ/GDAL datum support may be limited in the Wasm build) — into a browser tab. The browser fetches a Parquet file once from S3, loads it into local memory, and then evaluates every subsequent user interaction (slider drag, text filter, spatial join) as a local SQL query with no network round-trip. This "Frontend Database" pattern is why the filtering feels instant after the initial data load.

### 2. Columnar Parquet Fetching in the Browser

DuckDB-Wasm respects Parquet's columnar structure: a query selecting only `name` and `category` fetches only those column byte ranges from the remote file, not the entire file. This is the same columnar predicate pushdown that makes DuckDB fast locally, now applied over HTTP Range Requests in the browser. Watch the Network Tab — each query issues targeted range requests against the `.parquet` file, not a full download.

### 3. Zero Backend Cost and Local Privacy

Eliminating the always-on database server means the product costs only static file hosting (S3/R2) — no compute to scale, no server to patch. For sensitive datasets, local-only processing means user data never leaves their device. Both advantages compound: complex analytical queries on private data can run at scale with no backend infrastructure.

## 1. The "Frontend Database" Pattern

Traditionally, a web map sends a request to a server, the server queries a
database, and the results come back. This creates a "Loading..." spinner every
time the user pans or filters.

With **DuckDB-Wasm**:

1. **Direct Data Fetch**: The browser downloads a compressed data file (e.g., a
   10MB Parquet file) directly from cloud storage.
2. **In-Browser SQL**: DuckDB-Wasm loads that file into browser memory.
3. **Millisecond Latency**: Every time the user drags a slider or types a
   search, the browser runs a SQL query on its own local memory. No network
   overhead.

## 2. Why This Matters for Product Patterns

- **Zero Backend Cost**: You eliminate expensive, always-on database servers.
  You only pay for static file hosting (S3/R2).
- **Instant UX**: "Latency-Free Analysis" makes your product feel significantly
  more premium.
- **Local Privacy**: You can perform analysis on sensitive user data without it
  ever leaving their device.

## Practical Exercises

Build a high-speed analytical dashboard and a client-side spatial join — both powered by DuckDB-Wasm running entirely in the browser, with no backend server.



### Running the Exercises

Since these are browser-based, you'll need a local web server to handle the Wasm
files and Parquet range requests correctly. Run `python3 -m http.server 8000`
from the `src/exercises/browser-engine/` directory, then open
[http://localhost:8000](http://localhost:8000).

### What to Observe

- **The Spatial Extension**: Notice the `INSTALL spatial; LOAD spatial;` command
  in the spatial exercise. This is a full GEOS/GDAL-powered engine inside your
  Chrome/Firefox tab!
- **Parquet Performance**: Watch the network tab. DuckDB only fetches the
  specific "columns" needed for your query, not the entire file.
- **No Spinners**: Once the data is cached, filtering is limited only by your
  CPU speed, not your internet connection.
