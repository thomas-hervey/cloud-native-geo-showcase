## Overview

Building a STAC catalog means automating the metadata layer that connects processed data files to the tools that discover and consume them. Individual STAC Items become queryable collections by linking them through a catalog hierarchy — either as static JSON files on S3 (no server required) or as a dynamic STAC API backed by PgSTAC. The key pattern is registering metadata at the end of every processing pipeline rather than as a manual afterthought.

## Key Concepts

### 1. The Producer Pattern — Automated Catalog Registration

Metadata rot happens when data is added to S3 but the catalog isn't updated. The fix is treating STAC registration as the final step of every processing pipeline: the pipeline already knows the spatial extent, timestamp, and file path — it should write the STAC Item immediately. This shifts cataloging from a manual QC task to an automatic pipeline output.

### 2. Static vs. Dynamic STAC Architecture

Static STAC stores a collection of JSON files alongside your data in S3 — no server, queryable via standard HTTP, extremely cheap and resilient. Dynamic STAC (a STAC API backed by PgSTAC) provides a REST endpoint for filtering millions of items by geometry, time range, or property. Choose static for small-to-medium catalogs; choose dynamic when users need server-side search across global-scale holdings.

### 3. Zero-Copy Sharing and Standard Tooling

Once data is registered in a STAC catalog, different teams can discover and consume it without copying the underlying files. Open-source browsers, QGIS plugins, `stackstac`, and `pystac-client` all understand the STAC standard — the catalog becomes a universal interoperability layer over your data lake.

## 1. The Producer Pattern

A major product failure in geospatial engineering is **Metadata Rot**. This
happens when data is added or updated on S3, but the catalog isn't notified.

- **Manual Cataloging**: (What we did in the STAC module) Creating JSONs by hand. Fine for
  learning, impossible for production.
- **Automated Registration**: The final step of every processing pipeline should
  be "Register in STAC". The pipeline knows the spatial extent, the timestamp,
  and the file path—it should write the STAC metadata immediately.

## 2. Static vs. Dynamic Architecture

- **Static STAC**: A collection of JSON files stored alongside your data (e.g.,
  in the same S3 bucket). It requires **no server**. Clients read the JSONs via
  standard HTTP. This is extremely cheap and resilient.
- **Dynamic STAC (STAC API)**: A searchable database (like PgSTAC) that provides
  a REST API. Best for global-scale discovery where users need to filter
  millions of items.

## 3. Product Benefits

- **Zero-Copy Sharing**: Different teams can query the same STAC catalog without
  needing to move or copy the actual heavy data files.
- **Standard Tooling**: Once data is in STAC, you can use open-source browsers,
  QGIS plugins, and libraries like `stackstac` out-of-the-box.

## Practical Exercises

Simulate the final ingestion step of an ETL pipeline — crawl a directory of processed images, use `rasterio` and `pystac` to extract spatial metadata and generate a static STAC catalog, then validate the output with the STAC validator.



### What to Observe

- **Metadata Extraction**: Notice how we use `rasterio` to pull the spatial
  bounding box and CRS directly from the files.
- **Hierarchical Linking**: Watch how `pystac` automatically handles the `root`,
  `parent`, and `child` links between files.
- **Validation**: We'll use the internal STAC validator to ensure our output is
  technically correct.
