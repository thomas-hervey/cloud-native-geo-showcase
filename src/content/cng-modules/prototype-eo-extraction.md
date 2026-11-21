---
title: "Prototyping EO Feature Extraction (Esri/Element84 Style)"
---

> Exercises are implemented and verified end-to-end. See `src/exercises/eo-extraction/`.

## Overview

This prototype automates earth observation feature extraction — using computer vision models to detect roads, buildings, or vegetation boundaries in satellite imagery. It covers the full pipeline from COG tile sampling to model inference to GeoJSON output, including the critical step of georeferencing vision-model outputs from pixel space back to WGS84 coordinates. The gap between detection and georeferencing is what makes EO feature extraction harder than standard computer vision.

## Key Concepts

### 1. COG Range Requests

A Cloud-Optimised GeoTIFF stores image tiles in a predictable spatial index.
An HTTP client can send `Range: bytes=X-Y` to fetch only the tiles that overlap
a bounding box — no full download. `rioxarray.open_rasterio()` handles this
transparently when given an HTTPS URL. A full Sentinel-2 scene is roughly 900 MB; a single SF chip fetched this way is under 5 MB — less than 1% of the file.

### 2. Pixel → World Coordinate Transform

Every georeferenced raster has an affine transform that maps pixel (col, row)
to coordinates in the raster's native CRS. For Sentinel-2 COGs this is
typically a UTM projection (e.g., EPSG:32610), not WGS84 lon/lat. The transform applies pixel width and height offsets from the origin, then a second reprojection step (using `da.rio.crs` and GeoPandas `.to_crs("EPSG:4326")`) converts to true lon/lat. When a vision model returns polygons in pixel space, these two steps are how you get them back onto a map.

### 3. VLMs for EO — What to Expect

At Sentinel-2's 10m resolution, individual buildings are 2–5 pixels wide.
Claude Vision will over-segment large buildings, invent edges on parking lots and shadows, and produce inconsistent results across runs. This is not a failure — it's the lesson. VLMs are semantically powerful but not spatially precise. Purpose-built segmentation models (SAM, fine-tuned U-Nets) consistently outperform them on structured extraction tasks because they optimize for edge detection, not language understanding. The exercises use Claude Vision because it runs anywhere without a GPU.

### 4. VLM vs. SAM

| | Claude Vision | SAM (Segment Anything) |
|---|---|---|
| Cost | Cents per chip at API pricing (check current rates) | Free (model weights) |
| Setup | API key only | PyTorch + 2.5 GB model |
| Hallucination | Yes, common on EO | No (segments real edges) |
| Accuracy | Low–medium at 10m res | High |
| Best for | Exploration, hard-to-label tasks | Production extraction |

Element 84 and Esri's ArcGIS Image Analyst can extract vector features (building
footprints, roads, vegetation) directly from imagery using foundation models.
This module builds a lightweight version: search a STAC catalog for a Sentinel-2
scene over San Francisco, stream just the pixels you need via COG range requests,
pass an imagery chip to Claude Vision, and georeference the extracted polygons
back to WGS84 coordinates. The resulting GeoJSON gets a STAC item for provenance.

---

## What You'll Build

A Python pipeline that:

1. Searches the Element 84 Earth Search STAC API for a low-cloud Sentinel-2 L2A
   scene over SF (no auth needed — it's AWS Open Data)
2. Reads a spatial window (Mission/SOMA bounding box) from the COG using HTTP
   range requests — no full download
3. Converts the chip to PNG and passes it to Claude Vision with a structured
   prompt asking for building footprints as pixel-space GeoJSON
4. Applies the COG's affine transform to convert pixel coordinates → WGS84
5. Writes the georeferenced footprints to GeoJSON + GeoParquet
6. Creates a minimal PySTAC item in `output/stac_catalog/`

The resulting GeoJSON can be loaded into Scout alongside places and buildings,
or dragged into kepler.gl for quick visual inspection.

## Practical Exercises

Build a two-part pipeline: first stream a Sentinel-2 COG chip via HTTP range requests with NDVI computation, then pass that chip to Claude Vision and georeference the extracted building footprints back to WGS84.



### Exercise 1: `01_stream_cog.py` — Stream COG Imagery

Uses `pystac_client` to find a Sentinel-2 L2A scene over SF, then reads
a Mission/SOMA bounding box chip via COG range requests:

- Searches Element 84 Earth Search STAC API (free, no auth)
- Reads the `visual` (RGB) COG asset with `rioxarray`
- Visualises the RGB chip with matplotlib, saves `output/sf_rgb_chip.png`
- Prints a bandwidth estimate: uncompressed chip pixel size vs. full file size
  (a proxy for COG efficiency; actual HTTP bytes are smaller due to compression)
- Bonus: reads B04 + B08 bands separately and computes NDVI

### Exercise 2: `02_vision_inference.py` — Extract Features with a Vision Model

Passes the RGB chip to Claude Vision and georeferences the results:

- Re-fetches the same chip
- Calls `claude-opus-4-5` with a structured prompt requesting pixel-space GeoJSON
- Applies the COG's affine transform: pixel coords → WGS84 lon/lat
- Flags out-of-bounds geometries as likely hallucinations
- Writes `output/sf_buildings_vlm.geojson` and `output/sf_buildings_vlm.parquet`
- Creates a minimal PySTAC item in `output/stac_catalog/`
- Prints a hallucination analysis and per-chip cost estimate

Requires `ANTHROPIC_API_KEY` in `.env.local` at the project root.

### What to Observe

Open `output/sf_buildings_overlay.png` after running both exercises and ask:

- **Do the polygons land on actual buildings** or on roads/parking lots?
- **Are confidence scores calibrated?** Do high-confidence features look more
  like buildings than low-confidence ones?
- **What's the cost to cover all of SF?** The script prints an estimate.
  Compare to the cost of running SAM locally (approximately zero per chip).
- **Bandwidth:** Exercise 1 prints bytes fetched vs. full file size. How small
  a fraction of the COG did we actually read?
