## Overview

Geospatial pipelines fail silently — geometry topology breaks, coordinate systems drift, and datasets go stale without raising errors. Data quality, lineage tracking, and observability are the practices that catch these failures before they reach users. This module covers how to define measurable integrity standards, automate validation as a pipeline gate, and trace failures back to their source through lineage.

## Key Concepts

### 1. Data Integrity Checks — Schema Validation and Geometry Validity

Integrity checks fall into three categories: geometric (topology, projection, precision), metadata/schema (type drift, STAC compliance, enum consistency), and contextual (temporal freshness, spatial coverage, versioning). Treating these checks as automated pipeline guards — analogous to unit tests for code — prevents "Garbage In, Garbage Out" scenarios that destroy user trust downstream.

### 2. Data Lineage and Provenance Tracking

In a cloud-native stack, data flows through multiple zero-copy systems (S3 → DuckDB → Lonboard). Lineage allows you to trace a visual artifact on a map back to the specific version of the GeoParquet file that caused it. Without provenance tracking, a bad geometry discovered at render time requires manual archaeology through the entire pipeline.

### 3. Monitoring and Alerting Patterns for Pipeline Health

Geospatial SLIs (Service Level Indicators) and SLOs (Service Level Objectives) formalize "the data looks okay" into measurable targets: freshness within 24 hours, 100% coordinate validity, zero self-intersecting polygons, consistent CRS across all features. The consumption-first monitoring pattern — measuring at the API or tile server rather than at ingestion — ensures the entire pipeline is healthy, not just the S3 bucket.

## 1. The Three Pillars of Spatial Integrity

To build robust products, you must look beyond just "valid polygons." We
categorize integrity into three pillars:

### A. Geometric Integrity (The Shape)

- **Topology**: Ensuring coordinates follow OGC rules (e.g., no
  self-intersections).
- **Projection Mismatches**: Detecting "Coordinate Drift" (e.g., data labeled as
  WGS84 but containing high-precision Web Mercator meters).
- **Precision Loss**: Managing rounding errors during format conversions (e.g.,
  GeoJSON to Protobuf).

### B. Metadata & Schema Integrity (The Label)

- **Schema Drift**: Monitoring for unexpected data type changes (e.g., a
  "priority" column shifting from integers to categories).
- **Metadata Compliance**: Ensuring every dataset has mandatory STAC-compliant
  tags (source, date, license).
- **Attribute Consistency**: Validating that enum values (e.g.,
  `BuildingStatus`) match the master list.

### C. Contextual & Operational Integrity (The System)

- **Temporal Integrity**: Detecting staleness (e.g., is this real-time sync
  actually 48 hours old?).
- **Spatial Coverage**: Monitoring for "Silent Drops" where total bounding box
  area suddenly shrinks by 50% without an error code.
- **Versioning**: Ensuring that `v2.1` of a dataset is actually a delta from
  `v2.0` and not a complete architecture shift.

## 2. Implementing Spatial "Unit Tests"

Treating your data pipeline like production software means moving from **Manual
QC** to automated pipeline guards — the same discipline applied to code quality
applies to geospatial data quality:

- **Ingestion Guards**: Automated scripts that reject "dirty" data before it
  hits production.
- **Statistical Monitors**: Tracking daily ingest volume, average feature size,
  and bounding box centroids.
- **The "Quarantine" Pattern**: Programmatically routing broken data to a review
  bucket while allowing clean data to move to the map.

## 3. Why This Matters for Product Patterns

- **Reliability**: Prevents "Garbage In, Garbage Out" scenarios that destroy
  user trust.
- **Efficiency**: Catching errors at the _source_ (ingestion) rather than the
  _sink_ (the map) saves massive compute and compute-re-runs.
- **Compliance**: For legal or land-tenure products, history and versioning
  integrity is a regulatory requirement.

---

## 4. Geospatial Data Observability

Observability for geospatial data extends traditional data reliability practices
by measuring the **physical accuracy** and **spatial relationships** of your
information.

### Defining Geospatial SLIs and SLOs

To move from "the data looks okay" to a production-grade pipeline, you must
define **Service Level Indicators (SLIs)**—the specific metrics you measure—and
**Service Level Objectives (SLOs)**—the target goals for those metrics.

| Metric (SLI) | Target (SLO) | Why? |
| :--- | :--- | :--- |
| **Freshness** | Latest `updated_at` within < 24h | Users at the consumption layer need current data. |
| **Coordinate Validity** | 100% features in valid BBOX | Prevents map rendering failures or "off-planet" points. |
| **Topology Integrity** | 0 self-intersecting polygons | Required for accurate spatial joins and area calculations. |
| **SRS Consistency** | 100% features in EPSG:4326 | Prevents misalignment when overlaying multiple data sources. |

### The "Consumption-First" Monitoring Pattern

A common anti-pattern is monitoring only at the **Ingestion Layer**. If the data
is fresh on S3 but the catalog (STAC/Iceberg) is broken, the user sees old data.

**Product Pattern**: Measure freshness and quality at the **Consumption Layer**
(e.g., the API or Tiles server). This ensures that the entire pipeline—from
source to storage to metadata—is functioning correctly.

### Pipeline Lineage

In a cloud-native world, data often flows through multiple "zero-copy" systems
(S3 → DuckDB → Lonboard). **Lineage** allows you to trace a quality failure
instantaneously from a visual artifact on a map back to the specific version of 
the GeoParquet file that caused it.

## Practical Exercises

Build a "Self-Healing" router that validates a multi-failure dataset, routes broken records to a quarantine bucket, and visualizes failure modes — covering all three integrity pillars with Shapely, PyProj, and DuckDB.


