## Overview

Spatial data warehousing moves geospatial queries from local tools to distributed cloud engines — BigQuery, Snowflake, and Databricks — that can join billions of rows across `ST_INTERSECTS`, `ST_GEOGFROMWKB`, and H3 hexagonal grid hierarchies without managing a GIS server. The modern pattern pairs these warehouses with GeoParquet on cloud storage and Apache Arrow connectors, so data flows from warehouse to visualization tool without copying or serializing.

## Key Concepts

### 1. Zero-Copy Data Sharing via External Tables

Modern warehouses like Snowflake and BigQuery can query GeoParquet files directly on S3/GCS without loading them into the warehouse first. External tables expose raw Parquet as a queryable relation — new data on S3 is instantly queryable in the dashboard. Apache Arrow connectors then move query results to visualization tools like Lonboard with zero serialization overhead.

### 2. Spatial SQL at Warehouse Scale

BigQuery's `GEOGRAPHY` type and Snowflake's `GEOMETRY`/`GEOGRAPHY` types expose the same spatial function vocabulary as DuckDB — `ST_INTERSECTS`, `ST_DWithin`, `ST_GEOGFROMWKB` — but backed by distributed compute across billions of rows. The DuckDB module is a local rehearsal for the same spatial SQL patterns that run at petabyte scale in these warehouses.

### 3. The Warehouse-to-Map Pattern

Companies like Felt have pioneered direct Snowflake-to-map integration — eliminating the GIS server layer entirely. The warehouse becomes the single source of truth; maps and dashboards query it live rather than from a cached tile server. This pattern delivers cost efficiency (pay per query, not per always-on server), velocity (new S3 data is immediately visible), and collaboration (all teams work from the same tables).

## 1. Zero-Copy Data Sharing

The biggest trend in modern data infrastructure is eliminating **[ETL](https://en.wikipedia.org/wiki/Extract,_transform,_load)** (Extract, Transform, Load — the traditional pipeline that moves and formats data between systems). 
Instead of moving data from a storage bucket into a database, modern warehouses
like **Snowflake**, **Databricks**, and **BigQuery** can query **GeoParquet**
files directly on cloud storage.

- **External Tables**: Read-only access to files on cloud storage
  (S3/GCS/Azure).
- **Native Connectors**: Most modern warehouses now provide high-performance
  Python connectors that speak **[Apache Arrow](https://arrow.apache.org)** (a
  columnar in-memory format that enables zero-copy data transfer), allowing for
  instant transfer to visualization tools like
  **[Lonboard](https://developmentseed.org/lonboard/)** (a high-performance
  map-rendering library built on top of Deck.gl for Python).
- **Iceberg Support**: Native support for Apache Iceberg makes geospatial data
  lakes highly performant and schema-stable.

## 2. Spatial SQL at Scale

Modern data warehouses use highly optimized distributed compute to run spatial
joins across billions of rows.

- **BigQuery**: Native `GEOGRAPHY` support with functions like `ST_GEOGFROMWKB`
  and `ST_INTERSECTS`.
- **Snowflake**: Native `GEOGRAPHY` and `GEOMETRY` data types with extremely
  fast indexing and search.

## 3. Why This Matters for Product Patterns: Warehouse-to-Map

Companies like **[Felt](https://felt.com)** have pioneered the "Warehouse-to-Map" workflow. By
integrating directly with **[Snowflake](https://www.snowflake.com/en/data-cloud/solutions/geospatial-data-cloud/)**, Felt allows organizations to create
live-syncing dashboards without ever managing a GIS server. The Warehouse acts
as the "Single Source of Truth."

This pattern has clear advantages for any team working with geospatial data:

- **Cost Efficiency**: You only pay for the compute you use.
- **Velocity**: New data in S3 is instantly queryable in the dashboard.
- **Collaboration**: Marketing, Ops, and GIS teams all work off the same tables.

## Practical Exercises

Simulate warehouse patterns locally with DuckDB, then connect to real Snowflake or BigQuery endpoints — covering external table access, spatial SQL at scale, and zero-copy Arrow visualization with Lonboard.


