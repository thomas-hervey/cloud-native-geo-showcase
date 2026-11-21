## Overview

For years, **Shapefiles** and **GeoJSON** have been the standard for vector data
(points, lines, polygons). However, they face significant **complexity overhead** as datasets grow. The row-oriented nature of GeoJSON and the overhead of scanning large Shapefiles make them inefficient for massive, cloud-scale analysis.

- **GeoJSON**: Text-based (JSON), verbose, slow to parse (the entire file must
  be read into memory).
- **Shapefile**: Multi-file mess (.shp, .shx, .dbf), column limits, truncated
  names.

The modern cloud-native solutions are **GeoParquet** (analytics) and
**FlatGeobuf** (streaming visualization).

## Key Concepts

### 1. GeoParquet

Parquet is the gold standard for big data analytics (columnar storage).
**GeoParquet** adds a standardized way to store geometry in Parquet columns
(usually WKB binaries) and metadata (projection/CRS).

- **Columnar**: If you only want the "population" column, you don't read the
  "geometry" or "name" columns.
- **Compression**: Highly efficient compression (Snappy, Zstd).
- **Cloud Friendly**: Supports HTTP range requests beautifully.

### 2. FlatGeobuf

Designed specifically for the web. It is a flat binary format that allows for
**spatial indexing** within the file. This means a web map can query "give me
features in this bounding box" from a static file on S3 without a server in the
middle.

## Why This Matters for "Scout"

For our capstone project "Scout", we will deal with **Overture Maps** data
(millions of building footprints).

- GeoJSON would be hundreds of gigabytes and crash the browser.
- **GeoParquet** reduces this to manageable sizes and allows us to use
  **[DuckDB](https://duckdb.org)** to query it efficiently. 

### Why DuckDB?

[DuckDB](https://duckdb.org) has become the "standard library" for local geospatial analytics. It is a high-performance, in-process analytical database (like SQLite, but optimized for columns).

For geospatial work, the [DuckDB Spatial](https://duckdb.org/docs/extensions/spatial) extension allows it to:
1. **Read GeoParquet directly**: No need to "import" data; just query the files on disk or S3.
2. **Handle Geometry**: Perform spatial joins and filters at lightning speed.
3. **Bridge the Gap**: It's the perfect tool for moving from GeoJSON to GeoParquet.

We'll dive much deeper into this in our [Spatial SQL with DuckDB](/product-patterns/duckdb-spatial) module.

## Practical Exercises

A single benchmark script generates 100,000 random points and compares GeoJSON
versus GeoParquet across write time, file size, and read speed — making the
columnar advantage concrete and measurable.



## Expected Output

You should see that GeoParquet is significantly faster to write (often 10x in our test with this dataset) and
produces files that are usually 50-80% smaller than GeoJSON (in our test with this dataset). The read speed,
especially when selecting a subset of columns, is orders of magnitude faster.

## Next Steps

We have established our core file formats:

1. **COG** for Rasters.
2. **Zarr** for N-D Arrays.
3. **GeoParquet** for Vectors.

Next, we will look at how to organize massive collections of these files using
**Apache Iceberg**, which effectively turns your S3 bucket into a SQL database.
