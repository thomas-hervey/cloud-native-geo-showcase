## Overview

Modern geospatial analytics has moved beyond server-rendered tile images toward GPU-accelerated, interactive rendering that runs directly in the browser or notebook. Tools like Lonboard and deck.gl shift the rendering work to the client GPU, making it practical to visualize millions of points with smooth interactivity. At large scale, the bottleneck isn't compute — it's how data moves from cloud storage to the renderer. Cloud-native formats (COG, PMTiles, GeoParquet) let you stream only the bytes you need, eliminating full dataset downloads entirely.

## Key Concepts

### 1. GPU-Accelerated Rendering vs. Server Tiles

Traditional GIS serves PNG tiles generated server-side — every pan and zoom triggers a round-trip. Modern tools like deck.gl and Lonboard send raw binary vector data directly to the GPU, which renders features natively. The result is fluid interaction on datasets with millions of features because the data is resident client-side, not just a picture of it.

### 2. Cloud-Native Source Reading Without Downloading

COGs, PMTiles, and GeoParquet all support HTTP range requests, meaning a tool like DuckDB or TiTiler can read exactly the byte ranges relevant to the current viewport or query. This makes it possible to work against multi-terabyte datasets hosted on S3 without copying anything locally.

### 3. Composable Visualization Stack

No single tool handles every case well. Lonboard excels at large vector datasets in Python notebooks; TiTiler handles raster COG streaming as a serverless function; DuckDB-Wasm + deck.gl powers in-browser analytics. The right pattern is to pick the renderer that matches your data type, scale, and deployment target — and wire them together rather than reaching for a monolithic MapServer.

## 1. The Death of the Tiling Server

In a traditional "Cloud GIS" setup:

1. You request a map area.
2. A backend server queries a database.
3. The server draws a PNG image (tiling).
4. The server sends the PNG to your browser.

In a **Cloud-Native Viz** setup:

1. You query exactly what you need (DuckDB/Parquet).
2. The raw binary data is sent to your browser/notebook.
3. Your **GPU** renders the features instantly using technologies like **WebGL**
   or **deck.gl**.

## 2. Lonboard & GeoArrow

**Lonboard** is the bridge between Python and high-performance web maps. It uses
**GeoArrow**, a binary format specifically designed for fast transfer of vector
data between memory contexts (like from CPU to GPU).

Benefits of this approach:

- **Scale**: Visualize millions of points or polygons without lag.
- **Interactivity**: Every feature is "hot." You can hover over any point to see
  its attributes because the data is _there_, not just an image of it.
- **Simplicity**: No need for a complex MapServer or GeoServer.

## 3. Serverless Tiling with TiTiler

For raster data (COGs), we use **TiTiler**. It's a "dynamic tiling" server that
runs as a serverless function (AWS Lambda). It reads only the byte ranges of the
COG needed for a specific view and generates pixels on-the-fly.

## Practical Exercises

You'll compare legacy server-tile rendering against GPU-side rendering using Lonboard and deck.gl, and observe how GeoArrow enables low-latency interactivity on a 50,000+ feature dataset — all without a dedicated MapServer.



## Why This Matters for Scout

**Scout** will use **DuckDB-Wasm** and **Deck.gl** to perform this exact
"GPU-side" rendering directly in your web browser. This module proves that we
can handle planetary-scale data and still provide a smooth, interactive
experience.
