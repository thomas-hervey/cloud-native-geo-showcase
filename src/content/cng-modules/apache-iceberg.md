## Overview

In previous modules, we learned about **File Formats** (COG, Zarr, GeoParquet).
But how do you manage millions of these files as a single cohesive unit? How do
you update data safely without breaking existing queries?

Enter **Apache Iceberg**, a high-performance open table format for huge analytic
datasets. Iceberg sits above your raw Parquet files and adds ACID transactions,
schema evolution, partition management, and time travel — turning a folder of
files into something that behaves like a proper database table.

## Key Concepts

### 1. The Table Format Abstraction

Iceberg adds a metadata layer on top of Parquet files that makes them behave
like a single versioned table. Instead of querying a folder of files directly,
query engines ask the Iceberg catalog for the current table state, then read
only the Parquet files that belong to that snapshot. This indirection is what
enables safe concurrent writes and schema evolution without touching the raw
data.

### 2. Hidden Partitioning

Iceberg handles partitioning internally, so the physical layout of files on
disk is invisible to query authors. You can change how data is partitioned
(e.g., from monthly to daily) without rewriting queries or breaking existing
consumers. For geospatial workloads, this means you can add spatial partitions
later as data grows, without a costly migration.

### 3. Time Travel and Snapshot Isolation

Every write to an Iceberg table creates a new snapshot rather than modifying
existing files. This means you can query any previous state of the table by
snapshot ID or timestamp — useful for auditing, reproducibility, and recovering
from bad ingestion runs. Snapshots are cheap: Iceberg only writes new metadata
and data files, leaving the old ones in place.

> [!TIP]
> **Think of Apache Iceberg as a massive digital library index.** 
> While GeoParquet files are the "books" on the shelves, Iceberg is the sophisticated catalog that tracks which books were added, which were updated, and lets you "time travel" to see exactly what the library looked like last Tuesday—all without moving a single book.

### Why Not Just Use Folders of Parquet Files?

1. **ACID Transactions**: Multiple writers can update the same table
   simultaneously without corruption.
2. **Schema Evolution**: Add, rename, or drop columns without rewriting the
   whole dataset.
3. **Partition Evolution**: Change how data is physically laid out (e.g., from
   monthly to daily) seamlessly.
4. **Time Travel**: Query previous versions of your data (great for auditing and
   reproducibility).

### Iceberg v3: Native Geospatial Support

As of the **Iceberg v3 specification**, geospatial data is no longer a
"side-car" but a natively integrated feature. 

1. **Native Primitive Types**: Iceberg v3 introduces first-class `geometry` and 
   `geography` types.
2. **Spatial Query Pruning**: Iceberg stores **bounding box metadata** for 
   spatial columns at the snapshot level. This allows query engines to skip 
   millions of files that don't intersect with your area of interest (AOI) 
   without ever touching the data files.
3. **OGC Alignment**: The implementation is designed for interoperability with
   standard spatial engines (like Snowflake, BigQuery, and DuckDB) by using 
   standardized encodings.

## Geospatial Fit

Iceberg is the perfect "OS" for a Cloud-Native Geospatial data lake. It allows
you to:

- Organize billions of **GeoParquet** files.
- Apply spatial partitions (e.g., world-wide Overture data).
- Query efficiently using **DuckDB** or **Dask** by only reading the relevant
  files.

## Table Structure: Catalog vs. Warehouse

After running the exercise, you'll notice two new items in your folder:
`iceberg_catalog.db` and a `warehouse/` directory. Understanding the difference
is key to how Iceberg works.

### 1. The Catalog (`iceberg_catalog.db`)

The human-readable "entry point". In our case, it's a SQLite database.

- **Purpose**: It stores a pointer to the **current metadata file**.
- **Role**: When you query a table, the engine asks the catalog: "Where is the
  latest version of `geo_tutorial.points`?" The catalog responds with a path to
  a JSON file in the warehouse.

### 2. The Warehouse (`warehouse/`)

The physical storage where the data and metadata live. Under
`warehouse/geo_tutorial/points/` you will find a `data/` folder containing the
raw Parquet files and a `metadata/` folder with a `metadata.json` snapshot
descriptor, a manifest list (`.avro`), and one or more manifest files listing
the data files in each snapshot.

- **Metadata Layer**: Instead of one giant file, Iceberg uses a tree of small
  files. This allows for massive scaling and "Time Travel"—to go back in time,
  Iceberg simply points to an older `metadata.json` file.
- **Data Layer**: The raw GeoParquet files. Notice that Iceberg creates new
  files rather than modifying old ones, which is why it's so safe and resilient.

## Practical Exercises

Two exercises walk through a complete local Iceberg workflow: initializing a
SQLite-backed catalog, appending two batches of geospatial points to create
snapshots, then querying the table with time travel and running spatial filters
via DuckDB.



## Next Steps

Now that we can manage massive vector datasets with Iceberg, we will look at
**Datacubes** to see how to align and analyze multi-temporal raster datasets at
scale.
