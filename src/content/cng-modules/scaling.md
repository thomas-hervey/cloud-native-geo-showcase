<!-- TODO: Review for expansion - does this module feel too short compared to STAC/Zarr? -->

## Overview

Geospatial datasets routinely exceed what a single machine can hold in memory —
global satellite archives, continental-scale elevation models, multi-decade
climate reanalyses. **Dask** is the standard Python library for scaling these
workloads beyond one machine by splitting arrays into chunks and distributing
computation across CPU cores or a cluster. The key insight is lazy evaluation:
Dask builds a task graph that describes *what* to compute, then executes it
efficiently only when you ask for the result.

## Key Concepts

### 1. Vertical vs. Horizontal Scaling

Vertical scaling means buying a bigger machine — more RAM, faster CPU — but
hits a hard ceiling at the limits of available hardware. Horizontal scaling
adds more machines (workers) to a cluster and is theoretically unbounded.
Cloud-native geospatial workflows are designed for horizontal scaling: chunked
formats like Zarr and COG let independent workers process separate pieces of a
dataset simultaneously, with no worker needing to see the whole thing.

### 2. Dask's Lazy Execution Model

When you perform operations on a Dask array or DataFrame, nothing is computed
immediately. Dask builds a **task graph** — a directed acyclic graph of
operations — and only executes it when you call `.compute()` (returns a result
in memory) or `.persist()` (keeps the result distributed across workers). This
model means you can chain expensive operations and inspect the graph before
committing any compute budget.

### 3. Chunks as the Unit of Parallelism

The chunk size you choose when loading a dataset determines how work is split
across workers. A Zarr or stackstac datacube broken into 1024×1024-pixel spatial
chunks lets Dask assign each chunk to a separate CPU core or remote worker.
Chunk size is a tuning knob: too small creates scheduler overhead; too large
limits parallelism and may overflow memory. Matching chunk size to your access
pattern (spatial vs. temporal) is one of the most impactful optimizations in
cloud-native geospatial.

## 1. Vertical vs. Horizontal Scaling

- **Vertical Scaling**: Getting a bigger computer (more RAM, faster CPU). This
  has an upper limit.
- **Horizontal Scaling**: Adding _more_ computers (workers) to a cluster. This
  is theoretically infinite.

## 2. Dask: The Engine for Parallel Geospatial

**Dask** is a flexible library for parallel computing in Python. It's the
standard for scaling `xarray` and `pandas` because it mirrors their APIs almost
exactly.

### The "Lazy" Execution Model

Dask uses **Lazy Evaluation**. When you tell Dask to "subtract the red band from
the NIR band," it doesn't actually do any math. Instead, it builds a **Task
Graph**—a recipe for how to do the math later.

Work is only performed when you call:

- `.compute`: Returns the result as a standard Python object (like a NumPy
  array).
- `.persist`: Triggers the computation but keeps the result in the RAM of the
  workers.

## 3. Chunks: The Unit of Parallelism

When loading a datacube with `stackstac`, you provide a `chunksize` that breaks
a large image into a grid of equally-sized tiles. Dask can then send different
chunks to different CPU cores (or even different servers) to be processed
simultaneously.

## Practical Exercises

One exercise sets up a local Dask cluster and processes multiple timesteps of
Sentinel-2 data in parallel, producing an NDVI time-series plot. Watch the Dask
dashboard at `http://localhost:8787` while it runs to see chunks being processed
across cores in real time.



### What to Observe

- **The Dashboard**: Dask provides a real-time diagnostic dashboard (usually at
  `http://localhost:8787`). If you open it while the script is running, you'll
  see "Progress Bars" for every chunk being processed.
- **Lazy Speed**: Notice that the "Graph Building" happens in milliseconds,
  while the "Compute" takes several seconds.
- **Visual Result**: The script saves a `ndvi_timeseries.png` plot, showing the
  seasonal trend of San Francisco's greenery.
- **Parallelism**: Watch your system monitor; you'll see all your CPU cores
  spike at once as Dask distributes the math!

## 4. Scaling beyond your Laptop

While we are using a "Local Cluster" here, the exact same code can be deployed
to:

- **Dask Gateway**: A managed service on Kubernetes.
- **Coiled / Saturn Cloud**: Cloud-hosted Dask platforms.
- **High Performance Computing (HPC)**: Using `dask-jobqueue` for Slurm/PBS
  clusters.
