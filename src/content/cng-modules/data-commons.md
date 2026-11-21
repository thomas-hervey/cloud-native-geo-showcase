## Overview

Open geospatial data commons — Overture Maps, Microsoft Planetary Computer, AWS Open Data, and STAC-indexed registries — provide global, analysis-ready datasets under open licenses in cloud-native formats. The defining property of a true data commons is that you can query it directly from cloud storage without downloading or hosting it yourself. What makes these platforms interoperable at scale is the combination of standardized formats (GeoParquet, COG, Zarr) and open catalog specifications (STAC) that any client can traverse programmatically.

## Key Concepts

### 1. What Makes a Data Commons

A geospatial data commons has three properties: an open license, a cloud-native format (GeoParquet, COG, Zarr), and a queryable catalog (STAC or equivalent). The open license makes data sharable; the format makes it streamable without ETL; the catalog makes it discoverable and filterable by spatial extent, time, and type without downloading assets first.

### 2. Key Platforms

**Overture Maps** (Amazon, Meta, Microsoft, TomTom) releases global buildings, places, roads, and divisions as GeoParquet on S3 and Azure, with a Global Entity Reference System (GERS) for stable feature IDs. **Microsoft Planetary Computer** provides petabyte-scale earth observation and climate datasets — Sentinel, Landsat, MODIS — behind a STAC API. **AWS Open Data** hosts thousands of datasets across domains, many STAC-indexed, covering elevation, weather, land cover, and more.

### 3. Querying Without Downloading

DuckDB's spatial extension can read GeoParquet directly from S3 via HTTP range requests, applying predicate pushdown and spatial filters inside the engine. STAC clients (PySTAC, pystac-client) let you enumerate assets and retrieve only the items matching your AOI and date range before fetching a single byte of raster data. The pattern is: catalog search → asset URL → range-request read — no intermediate storage required.

## 1. What is Overture Maps?

Overture is a collaboration between Amazon, Meta, Microsoft, and TomTom. It
provides high-quality, global geospatial data in **Cloud-Native formats**.

Key aspects of Overture:

- **Global Scale**: Billions of entities (buildings, places, roads).
- **Format**: Data is released as **GeoParquet** files on Amazon S3 and Azure.
- **Entity Identification**: The **Global Entity Reference System (GERS)**
  provides unique IDs for map features.

## 2. Querying the Commons (No Backend Needed)

Traditional GIS required you to download a PostgreSQL/PostGIS database or a
massive Shapefile. With Overture and DuckDB, you can query exactly what you need
directly from S3 using **HTTP Range Requests**.

### How it works:

1. **Metadata Discovery**: DuckDB reads the Parquet footer to understand the
   schema and column statistics.
2. **Predicate Pushdown**: If you query `WHERE type = 'building'`, DuckDB only
   downloads the "type" column chunks.
3. **Spatial Filtering**: Using `bbox` columns, we can skip files that don't
   overlap with our area of interest.

## Practical Exercises

You'll use DuckDB to query billions of Overture POIs directly from S3 using spatial SQL — no download, no local database — and verify that the results are immediately ready for analysis and mapping.



## Why This Matters for Scout

This module is a direct preview of our Capstone project. In **Scout**, we will
build a "Chat-to-Map" interface where an LLM translates your questions into SQL
queries just like this one!
