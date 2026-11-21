> **Live App & Exercise Access**: Interactive tools in this track (such as the
> live **Scout** interface or spatial evaluation tools) are **not yet public**.
> If you would like to test these applications, please **reach out to the
> author**.

## Overview

Phase 1 builds the data ingestion pipeline for Scout — fetching point-of-interest data from the Overture Maps Foundation's open S3 dataset, filtering it to a San Francisco bounding box, spatially sorting the output using a Hilbert curve for efficient browser querying, and writing a STAC catalog that describes the resulting GeoParquet file. The catalog produced here feeds directly into Phase 2's LLM prompt as a machine-readable data contract.

## Key Concepts

### 1. Overture Maps as a Cloud-Native Data Source

Overture Maps is an open-data consortium (Amazon, Microsoft, Meta, TomTom) that publishes a unified global map dataset as Parquet files on AWS S3, queryable directly over HTTP without downloading. The dataset is organized into themes (`places`, `buildings`, `transportation`, `base`); Scout uses the `places` theme filtered to the San Francisco bounding box. DuckDB's `httpfs` extension makes this a single SQL query against S3 — no cluster, no manual download.

### 2. The STAC Catalog as a Data Contract

Publishing a machine-readable STAC catalog after ETL creates a stable interface that the Phase 2 backend (LLM prompt construction), the Phase 3 frontend (DuckDB-Wasm queries), and future consumers can all depend on. The catalog encodes the schema, bounding box, category vocabulary, and file location — making it the single source of truth that prevents the LLM from hallucinating column names or inventing category values.

### 3. Spatial Sorting with the Hilbert Curve

A raw GeoParquet file from Overture has rows in arbitrary order. DuckDB's `ST_Hilbert` function maps 2D coordinates to a 1D integer that preserves spatial locality — nearby points in space get nearby integers on the curve. Writing the output sorted by Hilbert index lets DuckDB-Wasm skip entire row groups based on min/max statistics when the user queries a city-scale bounding box, following the same principle as COG range requests applied to the row dimension.

## 1. The Data Source: Overture Maps

**Overture Maps Foundation** is an open-data consortium (Amazon, Microsoft,
Meta, TomTom) that publishes a unified global map dataset released as Parquet
files on AWS S3. Unlike OpenStreetMap, which requires parsing XML dumps,
Overture is built to be cloud-native: it's queryable directly from S3 with no
download required.

The dataset is organized into **themes**:

| Theme            | Content                                             |
| ---------------- | --------------------------------------------------- |
| `places`         | Points of interest: cafes, parks, hospitals, hotels |
| `buildings`      | Footprints of structures worldwide                  |
| `transportation` | Road segments, connectors, restrictions             |
| `base`           | Land use, water bodies, land cover                  |

For Scout, we use the `places` theme, specifically a filtered slice covering
**San Francisco** (bounding box `-122.52, 37.70, -122.35, 37.84`).

The full global dataset is tens of gigabytes. The SF slice is only a few
megabytes, which is perfectly sized to serve from a static file host and query
in a browser.

## 2. Why DuckDB for ETL?

While **Apache Sedona** is powerful for petabyte-scale processing, it introduces
Spark overhead: a JVM cluster, a cluster manager (YARN/Kubernetes), and a
significant startup cost just to run a single query.

For our demo-scale task (reducing millions of rows to a few thousand),
**DuckDB** is the efficient choice:

- **Direct S3 Queries**: Using the `httpfs` extension, DuckDB reads Overture
  Parquet files over HTTP without requiring a cluster.
- **Local & Browser Execution**: The same SQL engine runs in a local Python
  script or inside a browser tab.
- **Spatial Awareness**: The `spatial` extension provides GEOS-powered geometry
  functions (`ST_Point`, `ST_DWithin`, `ST_Hilbert`) comparable to PostGIS.
- **High Performance**: DuckDB processes millions of rows per second on a single
  core, slicing a city from a global dataset in seconds.

A core product principle here is to **choose the simplest tool for the scale**.
Sedona is the right choice for an active Spark cluster and global coverage;
DuckDB is the right choice for immediate results on a single machine.

## 3. Product Patterns in ETL

The ETL design determines the quality of the downstream user experience:

- **File granularity is a UX decision**: Balancing one large GeoParquet versus
  many small ones trades initial load time for query flexibility. A single file
  for a city maximizes simplicity, while spatial partitions (e.g., H3 cells)
  maximize performance for global products. This decision belongs in the product
  requirements, not just the engineering design.
- **The STAC catalog is a data contract**: Publishing a machine-readable catalog
  creates a stable interface that the backend (LLM prompt), the frontend (DuckDB
  queries), and future consumers can depend on. The catalog defines the API
  versioning for your geospatial data.
- **Schema choices drive AI quality**: The categories and column names preserved
  in the output shape the questions Scout can answer. A PM who understands this
  relationship can write better acceptance criteria: "The system must support
  queries for all Overture primary category values present in the target
  bounding box."

## 4. Spatial Optimization: The Hilbert Curve

A raw GeoParquet file from Overture has rows in arbitrary order, meaning
features from Tokyo might be adjacent to features from Buenos Aires on disk.
When DuckDB-Wasm queries a bounding box for San Francisco, it would normally
need to scan every row group to find relevant entries.

**Spatial sorting** solves this. A **Hilbert curve** is a space-filling curve
that maps 2D coordinates (lat/lon) to a single 1D integer while preserving
locality: nearby points in space are assigned nearby integers on the curve.

By writing GeoParquet sorted by Hilbert index, DuckDB-Wasm can use **row group
statistics** (min/max Hilbert index per group) to skip entire chunks of the
file. This follows the same principle as COG range requests and GeoParquet
columnar access, applied to the row dimension.

DuckDB's spatial extension includes a built-in `ST_Hilbert` function that we use
as a sort key when writing the final output file.

## Practical Exercises

In these exercises you will fetch Overture Maps data directly from S3, filter it to San Francisco, write a spatially-sorted GeoParquet file, and generate a STAC catalog that Phase 2 will use to construct the LLM prompt.


