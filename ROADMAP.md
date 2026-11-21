# Cloud-Native Geospatial Tutorial Roadmap

This document outlines the long-term vision for this tutorial, including the
core curriculum and the "Scout" capstone project.

## Phase 1: Core Curriculum (Modules 01-13)

Status: Partially complete — Modules 01-05 done, 06-13 content written,
exercises planned.

- [x] **01 Introduction**: Project structure and UV setup.
- [x] **02 STAC**: Spatiotemporal Asset Catalogs and data discovery.
- [x] **03 COG**: Cloud Optimized GeoTIFFs, tiling, and range requests.
- [x] **04 Zarr**: N-dimensional arrays for weather and climate data.
- [x] **05 Vector Formats**: GeoParquet and FlatGeobuf.
- [ ] **06 Apache Iceberg**: Modern table formats for data lakes.
- [ ] **07 Datacubes**: `stackstac` and alignments.
- [ ] **08 Cloud Storage**: S3 patterns, Requester Pays, Signed URLs.
- [ ] **09 AI & ML**: Data preparation and inference pipelines.
- [ ] **10 Scaling**: Distributed compute with Dask and Ray.
- [ ] **11 Data Commons**: Overture Maps, Planetary Computer — content complete,
      exercises planned.
- [ ] **12 Modern Analytics Viz**: GPU-accelerated visualization with lonboard
      and TiTiler.
- [ ] **13 Geo Foundation Models**: The future of spatial AI.

---

## Phase 2: Performance & Product Patterns (Modules 14-21)

These modules focus on optimizing for infrastructure cost, data integrity, and
discoverability in enterprise-scale systems.

- [ ] **[14: Fast Legacy Hybrid](src/content/cng-modules/14-fast-legacy.md)**:
      High-speed ingestion of enterprise formats (FileGDB, GeoPackage).
- [ ] **[15: Geospatial Integrity & Observability](src/content/cng-modules/15-integrity-observability.md)**:
      Automated topology and validation checks.
- [ ] **[16: Spatial Data Warehousing](src/content/cng-modules/16-spatial-warehousing.md)**:
      Hybrid cloud architectures and external tables (Snowflake/BigQuery).
- [ ] **[17: Multidimensional Mastery](src/content/cng-modules/17-multidimensional-zarr.md)**:
      Handling climate and time-series data at scale with Zarr.
- [ ] **[18: Catalog Management](src/content/cng-modules/18-stac-catalog.md)**:
      Building discoverable data assets with STAC.
- [ ] **[19: Serverless Infrastructure](src/content/cng-modules/19-pmtiles.md)**:
      Eliminating tile servers with PMTiles.
- [ ] **[20: Global Grid Systems](src/content/cng-modules/20-h3-indexing.md)**:
      Indexing and real-time supply/demand matching with H3.
- [ ] **[21: Client-Side Engine](src/content/cng-modules/21-browser-engine.md)**:
      Full-stack geospatial without a backend (Introduction to DuckDB-Wasm).

---

## Elective Applied Projects (Mastery Tracks)

Standalone projects designed to demonstrate platform-specific mastery and modern
architectural patterns.

- **[Applied: Urban Heat Island Monitor](src/content/applied/urban-heat-island.md)**:
  Automated Overture Maps processing with **Wherobots (Sedona)** and
  visualization in **Felt**.
- **[Applied: "Ghost Map"](src/content/applied/ghost-map.md)**: Real-time
  collaborative mapping using **Elixir/Phoenix WebSockets** to simulate Felt's
  architecture.

---

## Phase 3: "Scout" Capstone Project (Modules 22-25)

Status: ✅ Complete — `develop` branch

Scout is a **"Chat-to-Map"** application: the user types a natural language
question and gets an instant interactive map answer with zero backend servers or
databases.

| Layer             | Technology                       | Purpose                                                   |
| ----------------- | -------------------------------- | --------------------------------------------------------- |
| **Data**          | Overture Maps → GeoParquet on S3 | Spatially partitioned, queryable by range request         |
| **Semantic**      | Next.js API Route + LLM          | Translate natural language → DuckDB SQL                   |
| **Compute**       | DuckDB-Wasm in browser           | Query GeoParquet files directly from S3, no server needed |
| **Visualization** | MapLibre GL JS + Deck.gl         | Basemap + data overlay, zero-copy via Apache Arrow        |

- [x] [Module 22: Scout Intro & Architecture](src/content/cng-modules/22-scout-intro.md)
- [x] [Module 23: Phase 1 — ETL Pipeline](src/content/cng-modules/23-scout-phase1-etl.md)
      — DuckDB + Overture Maps, Hilbert sort, GeoParquet ETL. _Bonus:
      `04_ibis_exploration.ipynb` — Ibis API over DuckDB._
- [x] [Module 24: Phase 2 — Semantic Backend](src/content/cng-modules/24-scout-phase2-rag.md)
      — STAC-informed prompts, swappable LLM API route.
- [x] [Module 25: Phase 3 — Interactive Web App](src/content/cng-modules/25-scout-phase3-app.md)
      — MapLibre GL JS, DuckDB-Wasm, Deck.gl.

---

## Elective Extended Modules (26-35)

> Complete Modules 22-25 (the Scout build) before these. They extend Scout's
> architecture toward larger-scale, research-grade patterns.

| Module                                                      | Title                                          | Status                            |
| ----------------------------------------------------------- | ---------------------------------------------- | --------------------------------- |
| [26](src/content/cng-modules/26-vector-schema-rag.md)       | Vector Search & Schema RAG                     | 🔲 Planned                        |
| [27](src/content/cng-modules/27-agentic-geo-queries.md)     | Agentic Geospatial Queries                     | 🔲 Planned                        |
| [28](src/content/cng-modules/28-frontier-open-problems.md)  | Open Problems at the Geospatial AI Frontier    | ✅ Complete (reading module)      |
| [29](src/content/cng-modules/29-industry-analysis.md)       | Industry Analysis                              | ✅ Complete (reading module)      |
| [30](src/content/cng-modules/30-prototype-agentic-gis.md)   | Prototyping Agentic GIS (CARTO/Google Style)   | ✅ Complete                       |
| [31](src/content/cng-modules/31-prototype-nl-sql-web.md)    | Prototyping NL-to-SQL Web GIS (Felt Style)     | 🔲 Planned                        |
| [32](src/content/cng-modules/32-prototype-eo-extraction.md) | Prototyping EO Feature Extraction (Esri Style) | 🔲 Planned                        |
| [33](src/content/cng-modules/33-llm-geo-knowledge-eval.md)  | Where do LLMs think neighborhoods are?         | ✅ Complete (ongoing experiments) |
| [34](src/content/cng-modules/34-geopandas.md)               | GeoPandas Fundamentals                         | ✅ Complete                       |
| 35                                                          | Spatial SQL Deep Dive                          | 🔲 Planned                        |

### Module Summaries

- **Module 26**: When prompt stuffing breaks — embedding STAC catalog metadata
  into a vector store (ChromaDB, Qdrant, pgvector) for hybrid spatial + semantic
  retrieval.
- **Module 27**: Beyond single-turn NL-to-SQL: LLM tool-calling
  (`search_datasets`, `execute_sql`, `get_map_extent`), self-correcting SQL,
  observability.
- **Module 28**: Open problems survey — OGC standards gap, geospatial semantic
  similarity, hallucinated geographies, CRS heterogeneity, temporal geospatial
  semantics.
- **Module 29**: GeoAI landscape — Google, CARTO, Felt, Esri, Mapbox, Planet
  mapped against frontier open problems.
- **Module 30**: MCP server exposing four geospatial tools + LangGraph
  TypeScript agent with multi-step tool chaining. ✅ Complete.
- **Module 31**: Chat interface directly attached to MapLibre GL JS — natural
  language → DuckDB-Wasm spatial SQL in the browser.
- **Module 32**: Streaming COGs + vision-language model to extract building
  footprints into a STAC catalog.
- **Module 33**: LLM geographic knowledge eval — bounding box + polygon accuracy
  across SF neighborhoods, IoU metrics, model comparison.
  [Issue #39](https://github.com/thomas-hervey/cloud-native-geo-tutorial/issues/39)
  / [#40](https://github.com/thomas-hervey/cloud-native-geo-tutorial/issues/40)
  track ongoing polygon expansion work.
- **Module 34**: GeoPandas fundamentals — loading, CRS, spatial joins, geometry
  operations, choropleth mapping. Matt Forester's 6-notebook tutorial series
  with NYC open data. ✅ Complete.
- **Module 35** _(planned)_: Spatial SQL deep dive — raw DuckDB spatial
  extension (`ST_Within`, `ST_Buffer`, `ST_DWithin`), point-in-polygon joins,
  spatial aggregations. Reuses Module 34's NYC datasets.

---

## Project Structure Reference

```text
src/
├── app/
│   ├── cng-modules/           # CNG module list + individual module pages
│   ├── scout/                 # Scout capstone web app (Phase 3)
│   └── api/
│       ├── readme/            # Serves exercise README files to the UI
│       └── scout/query/       # Scout NL-to-SQL API endpoint (Phase 2)
│
├── content/
│   ├── cng-modules/           # Markdown content for CNG modules 01-32
│   └── applied/               # Markdown content for elective applied projects
│
├── exercises/                 # Hands-on code for CNG modules
│   ├── 02-stac/ … 21-browser-engine/
│   ├── 23-scout-etl/          # ETL + Ibis exploration
│   ├── 30-agentic-gis/        # MCP server + LangGraph agent
│   ├── 33-spatial-eval/       # LLM eval Streamlit app
│   └── 34-geopandas/          # GeoPandas tutorial notebooks + NYC data
│
└── scout/
```
