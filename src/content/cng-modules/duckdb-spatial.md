## Overview

DuckDB is the Swiss Army knife of local geospatial analysis. It is a fully
embedded, serverless analytical database that reads **GeoParquet, GeoJSON,
GeoPackage, Shapefile** and 50+ other formats via GDAL — without running a
server, without a Python daemon, and without loading data into memory upfront.

You have already *used* DuckDB throughout this curriculum: to query Overture
Maps in **Global Data Commons**, to drive the Scout ETL pipeline, and as the
SQL engine inside the browser via DuckDB-Wasm. This module teaches it as a
**standalone spatial skill** — from geometry types through R-tree indexing.

## Key Concepts

### 1. The Two-Stage Filter Pattern

Every fast spatial query against large files uses a two-stage approach: a cheap column filter that skips most rows before geometry is touched, followed by a precise geometry predicate that only runs on the remaining candidates. This is exactly the pattern behind the Overture Maps queries in **Global Data Commons** — the bbox column filter eliminates ~54% of rows before `ST_DWithin` ever evaluates a geometry.

### 2. Columnar Predicate Pushdown

GeoParquet stores data in columns. A query filtering on `category` only reads the `category` column — geometry is never touched. GeoJSON is a text format; the entire file must be parsed to evaluate any predicate. In benchmarks against the 42,492-row SF places dataset, GeoParquet column pushdown is 100–400× faster than a GeoJSON full scan. This gap is what makes querying Overture's multi-terabyte dataset feasible from a laptop.

### 3. R-Tree Spatial Indexing

DuckDB supports `CREATE INDEX ... USING RTREE` (since v1.3), which delivers order-of-magnitude speedups on spatial joins at disk-backed scale. R-tree indexes are most impactful for disk-backed `.duckdb` files and large datasets (>1M rows). For fully in-memory workloads on small datasets, DuckDB's query optimizer is often fast enough without an explicit index.

## What's New in DuckDB 1.5 (March 2026)

DuckDB 1.5 is a landmark release for spatial work:

- **GEOMETRY as a core type** — geometry is no longer limited to the spatial
  extension. Any extension can now produce and consume geometries natively.
- **CRS-aware geometry** — `GEOMETRY('OGC:CRS84')` embeds coordinate system
  metadata directly in the type. `typeof(geom)` tells you the CRS.
- **WKB shredding** — uniform geometry columns are stored as decomposed
  `STRUCT/LIST/DOUBLE` rather than opaque blobs, giving ~3× compression for
  point data (per the [DuckDB 1.5 announcement](https://duckdb.org/2026/03/09/announcing-duckdb-150)).
- **R-tree spatial indexing** (since v1.3) — `CREATE INDEX ... USING RTREE`
  delivers 58× speedup on spatial joins at disk-backed scale (per [DuckDB's spatial join benchmarks](https://duckdb.org/2025/04/07/spatial-joins.html)).

## Learning Objectives

By the end of this module you will be able to:

1. Load spatial data into DuckDB from GeoJSON (`ST_Read`), GeoParquet
   (`read_parquet`), GeoPackage (`ST_Read`), and CSV with lat/lon
2. Write spatial predicate queries: `ST_Intersects`, `ST_Contains`,
   `ST_Within`, `ST_DWithin`, `ST_Distance`
3. Understand and apply the **two-stage filter pattern** (bbox pre-filter +
   precise geometry predicate) — the pattern behind all fast Overture queries
4. Create R-tree spatial indexes and understand when they pay off
5. Explain and measure **columnar predicate pushdown** — why GeoParquet is
   100× faster than GeoJSON for attribute filters
6. Round-trip data between DuckDB and GeoPandas

## Geometry Type and CRS

When reading GeoParquet files written by GeoPandas or GDAL, DuckDB 1.5 reports
the column type as `GEOMETRY('OGC:CRS84')` — WGS84 geographic coordinates.
For R-tree indexing, cast to the base `GEOMETRY` type using `geometry::GEOMETRY`.

> **Note — WKB-in-Parquet vs GeoParquet (DuckDB 1.5 behavior)**: the Scout ETL outputs
> (`sf_places.parquet`, `sf_buildings.parquet`) store geometry as raw WKB bytes written via
> `ST_AsWKB(geometry)`. In DuckDB 1.5, `read_parquet()` **auto-decodes** these WKB columns
> and returns them as `GEOMETRY('OGC:CRS84')` — not a plain `BLOB`.
> This means **`ST_GeomFromWKB()` will fail** with a binder error because it only accepts `BLOB`.
> Always use the `::GEOMETRY` cast instead — it strips the CRS annotation and works on both
> plain `BLOB` and typed `GEOMETRY('OGC:CRS84')`.
> Proper GeoParquet files written by GeoPandas `to_parquet()` also return `GEOMETRY('OGC:CRS84')`;
> the `::GEOMETRY` cast is the safe, version-agnostic pattern for both file types.

## Distance in Degrees

DuckDB's `ST_DWithin` and `ST_Distance` operate in the units of the geometry's
CRS. For `EPSG:4326` (degrees), the conversion at SF's latitude (~37.7°N) is:

| Distance | Approx degrees |
|---|---|
| 500m | 0.0045° |
| 1 km | 0.009° |
| 2 km | 0.018° |

`ST_Transform` to a projected CRS (e.g., `EPSG:32610` UTM Zone 10N) requires
the PROJ library to be available. If `ST_Transform` returns `POINT (Infinity
Infinity)`, PROJ datum files are not bundled in your DuckDB install — use the
degree approximations above.

## Datasets

All exercises use pre-existing SF data — no downloads required.

| File | Location | Content |
|---|---|---|
| `sf_places.parquet` | `scout-etl/output/` | 42,492 SF POIs (Scout pipeline output) |
| `sf_buildings.parquet` | `scout-etl/output/` | 171,233 SF building footprints |
| `Analysis_Neighborhoods_20260309.geojson` | `spatial-eval/data/` | 41 SF neighborhood polygons |
| `countries.gpkg` | `legacy-ingest/data/` | 176 world countries (GDAL GeoPackage) |

## Practical Exercises

Build three exercises covering spatial predicates and measurements, multi-format I/O benchmarking, and R-tree indexing with the two-stage filter pattern — all using real SF Places and Buildings data from the Scout ETL pipeline.



### What to Observe

**Exercise 1** — The neighborhood restaurant choropleth shows which SF districts
are food-dense. Verify that the Mission and SoMa rank near the top. The Dolores
Park scatter plot should show ~50–80 food/drink places inside the 500m circle.

**Exercise 2** — The benchmark bar chart is the key output: GeoJSON read time
should be ~100–400× longer than GeoParquet. File size should be ~3× larger.
This is the same gap that makes Overture queries feasible at terabyte scale.

**Exercise 3** — The columnar pushdown chart shows why GeoParquet attribute
filters are ~150× faster than GeoJSON. The funnel chart shows the two-stage
filter eliminating ~54% of rows before any geometry evaluation runs — this is
the exact mechanism behind the query in **Global Data Commons**.

## Key Packages

`uv add "duckdb>=1.5.0" geopandas matplotlib`

| Package | Purpose |
|---|---|
| `duckdb` | Embedded SQL engine with spatial extension |
| `geopandas` | GeoPandas ↔ DuckDB round-trips and visualization |
| `matplotlib` | Choropleth maps and benchmark bar charts |

## Connections to Other Modules

- **(GeoPandas)**: Same spatial operations (`within`, `intersects`, `distance`)
  but in SQL. Compare `gdf[gdf.within(polygon)]` vs `WHERE ST_Within(geom, ?)`.
- **(Global Data Commons)**: Explains *why* the Overture query is fast — the
  two-stage filter pattern and GeoParquet pushdown are demonstrated here.
- **(WASM Engine)**: DuckDB-Wasm runs the same spatial extension client-side.
  Everything learned here applies in the browser.
- **(Spatial Warehousing)**: BigQuery/Snowflake use the same spatial function
  names (`ST_Intersects`, `ST_DWithin`, etc.) — DuckDB is a local rehearsal.
- **(Prototype: Agentic GIS)**: The MCP server returns DuckDB SQL. After this
  module, students understand exactly what those generated queries do.

## Further Reading

- [DuckDB Spatial Extension Overview](https://duckdb.org/docs/stable/core_extensions/spatial/overview)
- [DuckDB 1.5 Announcement — GEOMETRY as Core Type](https://duckdb.org/2026/03/09/announcing-duckdb-150)
- [Spatial Joins with R-Tree Indexing](https://duckdb.org/2025/08/08/spatial-joins)
- [DuckDB 1.5 Spatial Updates (Spatialists)](https://spatialists.ch/posts/2026/03/22-duckdb-15-with-spatial-updates/)
