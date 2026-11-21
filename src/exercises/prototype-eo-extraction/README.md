# Prototyping EO Feature Extraction

## What This Is

A two-exercise Python pipeline that shows how Esri and Element 84 style EO
feature extraction actually works under the hood — from finding imagery in a
STAC catalog, down to streaming just the pixels you need, passing them to a
vision model, and writing georeferenced results back out.

> **Prereq:** Complete the **Geo Foundation Models** module before this one.

## Exercises

| File | What It Teaches |
|---|---|
| `01_stream_cog.py` | COG range requests, STAC search, rioxarray, bandwidth comparison, NDVI |
| `02_vision_inference.py` | Claude Vision for building extraction, pixel→WGS84 transform, STAC provenance |

---

## Setup

These exercises use the shared `uv` environment at `src/exercises/`.

```bash
# From project root
cd src/exercises

# All dependencies are already in pyproject.toml.
# If you haven't set up the env yet:
uv sync
```

You also need an `ANTHROPIC_API_KEY` in `.env.local` at the project root for
Exercise 2. Exercise 1 is entirely free (public AWS data, no keys needed).

---

## Running the Exercises

```bash
# From src/exercises/

# Exercise 1 — stream a Sentinel-2 chip over SF
uv run python eo-extraction/01_stream_cog.py

# Exercise 2 — extract building footprints with Claude Vision
uv run python eo-extraction/02_vision_inference.py
```

Output files land in `eo-extraction/output/` (gitignored):

```
output/
├── sf_rgb_chip.png             # visual RGB chip
├── sf_ndvi_chip.png            # NDVI (bonus, Ex 1)
├── sf_buildings_vlm.geojson    # georeferenced footprints
├── sf_buildings_vlm.parquet    # same, as GeoParquet
├── sf_buildings_overlay.png    # chip + footprint overlay
├── claude_raw_response.json    # raw VLM response (useful for debugging)
└── stac_catalog/
    └── sf-buildings-vlm-<ts>.json   # STAC item
```

---

## Key Concepts

### COG Range Requests

A Cloud-Optimised GeoTIFF stores image tiles in a predictable layout with an
internal spatial index. An HTTP client can send `Range: bytes=X-Y` to fetch
only the tiles that overlap a bounding box, without downloading the full file.

```
Full Sentinel-2 scene: ~900 MB
Your SF chip:           < 5 MB
```

`rioxarray.open_rasterio()` handles range requests transparently when you pass
an HTTPS URL. The underlying library (`rasterio`) uses GDAL's `/vsicurl/`
driver which knows how to issue range requests to S3 and HTTP servers.

### Pixel → World Coordinates

Every georeferenced raster has an **affine transform** that maps pixel (col, row)
to coordinates in the raster's **native CRS** (e.g., UTM easting/northing for
Sentinel-2, *not* necessarily WGS84 lon/lat):

```
x = origin_x + col * pixel_width
y = origin_y + row * pixel_height   # pixel_height is negative for north-up
```

`rioxarray` exposes this as `da.rio.transform()`, and `da.rio.crs` tells you
which CRS the coordinates are in. For Sentinel-2 COGs the native CRS is a UTM
projection (e.g., EPSG:32610 for the Western US), so after applying the affine
transform you typically need a CRS transform to WGS84 lon/lat (e.g., via
GeoPandas `.to_crs("EPSG:4326")`). When Claude Vision returns polygon coordinates
in pixel space, Exercise 2 applies this two-step process to get real-world
coordinates onto a map.

### VLM vs. SAM

| | Claude Vision | SAM (Segment Anything) |
|---|---|---|
| Cost | ~$0.02–0.10 per chip | Free (model weights) |
| Setup | Just an API key | PyTorch + 2.5 GB model |
| Hallucination | Yes, common | No (it segments real edges) |
| Accuracy on EO | Low–medium | High |
| Good for | Exploration, labelling hard cases | Production extraction |

Exercise 2 uses Claude Vision because it runs anywhere without a GPU. The
`hallucination_report()` function at the end deliberately surfaces the problems
so you can see where VLMs fail on satellite imagery.

### Hallucination Patterns

At Sentinel-2's 10m resolution, individual buildings are often 2–5 pixels.
You should expect the VLM to:

1. **Over-segment** — return 5 polygons for a single large building
2. **Invent edges** — trace shadows or parking lot edges as building walls
3. **Drift in confidence** — flag real buildings with low confidence and
   invented features with high confidence
4. **Be inconsistent** — run the same chip twice and get different results

This is not a bug — it's the core lesson. VLMs are not geometric: they
understand images semantically, not spatially. A purpose-built segmentation
model (SAM, or a fine-tuned U-Net) will consistently outperform them on
structured extraction tasks.

---

## What to Observe

Run both exercises and then open `output/sf_buildings_overlay.png`. Ask yourself:

1. **Do the polygons land on actual buildings** or on roads/parking lots?
2. **Are the confidence scores calibrated** — do high-confidence features look
   more like buildings than low-confidence ones?
3. **What's the cost–coverage tradeoff?** The script prints an estimate. How
   much would it cost to cover all of SF?
4. **Bandwidth (proxy):** Exercise 1 prints an estimated uncompressed pixel data
   size for the window you read versus the full image. How small a fraction of
   the COG's pixels did we actually process?
---

## Loading Results in QGIS or kepler.gl

```bash
# QGIS
# Layer → Add Layer → Add Vector Layer → Browse to output/sf_buildings_vlm.geojson

# kepler.gl (browser)
open https://kepler.gl/demo
# Drag-drop output/sf_buildings_vlm.geojson onto the map
```

---

## Next Steps

- **LLM Geo Knowledge Eval** — systematic evaluation of what spatial
  reasoning LLMs can and can't do reliably.
- **SAM integration:** Install `segment-geospatial` (already in pyproject.toml
  as `segment-geospatial`) and follow the commented-out SAM block in
  `02_vision_inference.py` to compare against Claude Vision results.
- **Production pipeline:** See how Element 84's `titiler` and AWS Lambda can
  run this pattern at scale without a local Python environment.
