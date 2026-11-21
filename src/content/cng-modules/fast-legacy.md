## Overview

Legacy geospatial pipelines built on Python/GDAL process data one feature at a time — a model that breaks down at scale. Row-at-a-time reads through Fiona bindings, paging limits on Esri REST APIs, and verbose JSON parsing all compound into multi-hour ingestion jobs. Modern stacks replace these bottlenecks with columnar reads via PyOgrio, Arrow-backed in-memory transfers, and DuckDB as the query engine — turning what can be a multi-hour ingest into a sub-minute cached pipeline (depending on dataset size and network).

## Key Concepts

### 1. The Python/GDAL Bottleneck

Traditional Python geospatial libraries like Fiona use high-level C++ bindings that convert each feature from a native GDAL type to a Python object, one record at a time. For a 500 MB GeoPackage, this object-conversion overhead dominates total read time far more than I/O itself. The root cause is row-oriented processing in a world that has moved to columnar data.

### 2. Apache Arrow In-Memory Columnar Format

Apache Arrow defines a language-agnostic columnar memory layout that libraries can share without copying data. PyOgrio reads GDAL files directly into Arrow buffers, which DuckDB, GeoPandas, and Lonboard can all consume without serialization. Zero-copy transfer between tools is what makes the modern stack fast — the same bytes move from disk to map without ever being converted to Python objects.

### 3. DuckDB as the Modern Geospatial ETL Engine

DuckDB reads GeoParquet, GeoPackage, Shapefile, and GeoJSON natively, applies SQL predicates before loading geometry, and outputs Arrow batches for downstream visualization. Replacing a live Esri REST API with a GeoParquet cache on S3 and pointing DuckDB at it changes query latency from seconds-per-page to milliseconds-per-result — a change that directly controls onboarding throughput.

## 1. The Bottleneck: Python vs. GDAL

Most Python geospatial libraries (like `fiona`) use slow, high-level bindings to
the underlying GDAL/OGR C++ library. When reading a 500MB GeoPackage, these
libraries spend a massive amount of time converting C++ data types to slow
Python objects.

## 2. Enter PyOgrio

**PyOgrio** is a modern, bulk-oriented binding to GDAL. Instead of reading one
feature at a time, it leverages **Arrow-backed** memory to pull data directly
into `geopandas` or `duckdb`.

**The Result**:

- **Ingestion Speed**: Up to 10x faster than traditional methods.
- **Memory Efficiency**: Lower overhead for large datasets.

## 3. The Proxy Pattern: GDAL Virtual Filesystems (VFS)

While cloud-native formats like COG and GeoParquet are designed for range
requests, many legacy files (Shapefiles, GeoPackages) are not. However, we can
still "proxy" these files using **GDAL Virtual Filesystems**.

GDAL includes a layer that allows it to treat remote files (S3, HTTP, Zip) as if
they were local files. This is the "proxy" that enables cloud-native-like
behavior for legacy data.

- **/vsizip/**: Read a Shapefile or CSV directly inside a ZIP file without
  unzipping to disk.
- **/vsicurl/**: Read a remote GeoPackage on a web server using HTTP Range
  Requests.
- **/vsis3/** / **/vsigs/**: Connect directly to AWS S3 or Google Cloud Storage.

**Example**:
`gpd.read_file("/vsizip//vsicurl/https://example.com/data.zip/data.shp")`

This allows you to keep legacy data in its original archival format while still
accessing it efficiently over the network.

## 4. Esri Enterprise & The REST API Bottleneck

Clients often rely on **Esri Enterprise Map and Feature Services**. These
services are typically hosted on-prem or in self-hosted enterprise environments
and serve data via a REST API.

### The Problem:

- **Large Hierarchies**: Enterprise environments often have deeply nested folder
  structures and thousands of layers.
- **Paging Limits**: REST APIs usually have a limit (e.g., 1000 or 2000
  features) per request. Pulling 1M features requires thousands of sequential
  HTTP calls, which is extremely slow.
- **Proprietary Format**: The JSON response from Esri Services is verbose and
  slow to parse.

### The "Local Cache" Pattern:

The modern solution for handling these legacy services in a cloud-native
pipeline is to implement a **Local Cache Sync**:

1. **Request**: Use the ArcGIS REST API `/query` endpoint to pull data.
2. **Stream**: Use specialized libraries (like `pyogrio` or `geopandas`) to
   stream the JSON into a GeoDataFrame.
3. **Serialize**: Immediately save the result to **GeoParquet** on S3/Cloud
   Storage.
4. **Analyze**: Point your modern tools (DuckDB, Athena, Lonboard) at the
   Parquet cache instead of hitting the live service.

## 5. Why This Matters for Product Patterns

Geospatial products almost always face **the Migration Problem**: users want
their existing data in the new system. The speed of your ingestion pipeline
directly controls how smoothly this works.

If pulling from a legacy Esri service takes hours per dataset, you can't
onboard users at scale. If it takes seconds to minutes — using the Local Cache pattern
above (results vary by dataset size and network) — you have a seamless, repeatable process that your whole team can rely
on.

This is the core engineering-to-product trade-off: **ingest latency = onboarding
friction**.

## Practical Exercises

Compare PyOgrio vs. Fiona ingestion speed, benchmark REST API paging against a GeoParquet local cache, and explore interactive visualization patterns that only become practical once ingestion is fast.


