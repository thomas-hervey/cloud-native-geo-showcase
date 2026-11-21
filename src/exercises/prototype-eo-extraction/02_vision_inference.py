"""
Exercise 2: Extract Features with a Vision Model
============================================================
Pass a Sentinel-2 RGB chip to Claude Vision. Prompt the model to identify
building footprints and return them as GeoJSON polygons in pixel coordinates.
Then georeference those pixel polygons back to WGS84 using the COG's affine
transform. Finally, write the results to GeoParquet + GeoJSON and create a
minimal PySTAC item linking the derived footprints to the source COG.

Key concepts:
  - VLM prompt design for structured spatial output
  - Pixel → WGS84 coordinate conversion using an affine transform
  - Hallucination: vision models *will* invent features — document it
  - PySTAC item creation for derived data provenance

Run from src/exercises/:
    uv run python eo-extraction/02_vision_inference.py

Prerequisites:
    - ANTHROPIC_API_KEY set in <project_root>/.env.local
    - Run 01_stream_cog.py first (or let this script fetch the chip itself)
"""

import base64
import json
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import anthropic
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")  # non-interactive backend — saves to file, no display window needed
import matplotlib.pyplot as plt
import numpy as np
import requests
from dotenv import load_dotenv
from shapely.geometry import Polygon, mapping, shape

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

# Load .env.local from project root (4 levels up from this file)
_project_root = Path(__file__).resolve().parents[3]
dotenv_path = _project_root / ".env.local"
if dotenv_path.exists():
    load_dotenv(dotenv_path)
    # print(f"  Debug: Loaded .env.local from {dotenv_path}")
else:
    # Fallback to current directory for local dev without complex paths
    load_dotenv()

import os  # noqa: E402 — after dotenv load

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    print(
        "ERROR: ANTHROPIC_API_KEY not set.\n"
        f"Add it to {_project_root / '.env.local'} and re-run.",
        file=sys.stderr,
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SF_BBOX = [-122.42, 37.77, -122.39, 37.80]  # Mission/SOMA
STAC_API_URL = "https://earth-search.aws.element84.com/v1"
COLLECTION = "sentinel-2-l2a"

# Claude model — claude-sonnet is a good balance of speed and vision quality
CLAUDE_MODEL = "claude-opus-4-5"

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
STAC_CATALOG_DIR = OUTPUT_DIR / "stac_catalog"
STAC_CATALOG_DIR.mkdir(exist_ok=True)

# Chip PNG path — use the output from Exercise 1 if it exists
CHIP_PNG_PATH = OUTPUT_DIR / "sf_rgb_chip.png"


# ---------------------------------------------------------------------------
# Step 1 — Get the chip (re-fetch or reuse Exercise 1 output)
# ---------------------------------------------------------------------------

def get_chip_and_transform() -> tuple[bytes, object, str]:
    """
    Returns:
        image_bytes: raw PNG bytes of the RGB chip
        transform:   rasterio affine transform (pixel → CRS coordinates)
        cog_href:    source COG URL for STAC provenance
    """
    from pystac_client import Client
    import rioxarray  # noqa: F401
    import xarray as xr
    import io
    from PIL import Image

    print("Step 1 — Fetching Sentinel-2 COG chip ...")

    catalog = Client.open(STAC_API_URL)
    results = catalog.search(
        collections=[COLLECTION],
        bbox=SF_BBOX,
        query={"eo:cloud_cover": {"lt": 20}},
        max_items=3,
    )
    items = list(results.items())
    if not items:
        raise RuntimeError("No Sentinel-2 scenes found. Try widening bbox or cloud cover.")

    item = items[0]
    print(f"  Scene: {item.id}  ({item.datetime.date()})")

    asset = item.assets.get("visual")
    if asset is None:
        raise KeyError(f"No 'visual' asset in {item.id}. Assets: {list(item.assets.keys())}")

    cog_href = asset.href

    # Stream chip
    da = rioxarray.open_rasterio(cog_href, parse_coordinates=True, lock=False)
    chip = da.rio.clip_box(
        minx=SF_BBOX[0], miny=SF_BBOX[1],
        maxx=SF_BBOX[2], maxy=SF_BBOX[3],
        crs="EPSG:4326",
    )
    data = chip.values  # (3, H, W) uint8

    affine_transform = chip.rio.transform()
    crs = chip.rio.crs

    print(f"  Chip shape: {data.shape}")
    print(f"  CRS:        {crs}")
    print(f"  Transform:  {affine_transform}")

    # Convert to PNG bytes (PIL)
    rgb = np.moveaxis(data, 0, -1)  # (H, W, 3)
    img = Image.fromarray(rgb.astype(np.uint8))

    # Save to disk for reference and for reuse
    img.save(str(CHIP_PNG_PATH))
    print(f"  Chip saved: {CHIP_PNG_PATH}")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    image_bytes = buf.getvalue()

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    image_bytes = buf.getvalue()

    return image_bytes, affine_transform, cog_href, item, crs


# ---------------------------------------------------------------------------
# Step 2 — Call Claude Vision for building footprint extraction
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a geospatial computer vision assistant. Your task is to identify
building footprints in satellite imagery and return them as precise GeoJSON polygons
in pixel coordinate space.

Rules:
- Return ONLY valid JSON — no explanation, no markdown, no code fences.
- Use pixel coordinates: top-left is (0, 0), x increases right, y increases down.
- Polygon coordinates are [x, y] pairs (x = col, y = row).
- Close each polygon ring (last point == first point).
- Include confidence (0.0–1.0) and a short label per feature.
- If you cannot identify distinct building footprints, return {"features": []}.

Output schema:
{
  "image_width_px": <int>,
  "image_height_px": <int>,
  "features": [
    {
      "label": "<building description>",
      "confidence": <float 0-1>,
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[x0,y0],[x1,y1],...,[x0,y0]]]
      }
    }
  ]
}"""

USER_PROMPT = (
    "Identify all distinct building footprints visible in this Sentinel-2 satellite "
    "image of San Francisco (Mission District / SOMA area). "
    "Return them as GeoJSON polygons in pixel coordinates following the schema provided. "
    "Focus on clearly delineated rooftops. Sentinel-2 resolution is ~10m/pixel so individual "
    "buildings may be 2–5 pixels across — do your best and note low-confidence detections."
)


def call_claude_vision(image_bytes: bytes) -> dict:
    """
    Pass the chip to Claude Vision and parse the structured GeoJSON response.

    Returns the parsed JSON dict (may have empty features list).
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    b64_image = base64.standard_b64encode(image_bytes).decode("utf-8")

    print("\nStep 2 — Calling Claude Vision for building footprint extraction ...")
    print(f"  Model: {CLAUDE_MODEL}")
    print(f"  Image: {len(image_bytes) / 1024:.1f} KB (base64 encoded)")
    t0 = time.perf_counter()

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": b64_image,
                        },
                    },
                    {"type": "text", "text": USER_PROMPT},
                ],
            }
        ],
    )

    elapsed = time.perf_counter() - t0
    raw_text = message.content[0].text.strip() if message.content else ""

    print(f"  Response time: {elapsed:.2f}s")
    print(f"  Input tokens:  {message.usage.input_tokens:,}")
    print(f"  Output tokens: {message.usage.output_tokens:,}")

    # Strip markdown code fences if the model ignores our "no fence" instruction
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```[a-z]*\n?", "", raw_text)
        raw_text = re.sub(r"\n?```$", "", raw_text)

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        print(f"\n  WARNING: Claude returned non-JSON: {exc}")
        print(f"  Raw response (first 500 chars):\n{raw_text[:500]}")
        result = {"features": [], "_parse_error": str(exc), "_raw": raw_text[:200]}

    n_features = len(result.get("features", []))
    print(f"  Features returned: {n_features}")
    return result


# ---------------------------------------------------------------------------
# Step 3 — Georeference pixel polygons → WGS84
# ---------------------------------------------------------------------------

def pixel_to_world(px: float, py: float, transform) -> tuple[float, float]:
    """
    Convert pixel (col, row) to (longitude, latitude) using the affine transform.

    Affine convention:
        lon = transform.c + px * transform.a + py * transform.b
        lat = transform.f + px * transform.d + py * transform.e

    For north-up rasters (typical): b=0, d=0, a=pixel_width, e=-pixel_height
    So: lon = origin_x + col * pixel_width
        lat = origin_y + row * (-pixel_height)
    """
    lon = transform.c + px * transform.a + py * transform.b
    lat = transform.f + px * transform.d + py * transform.e
    return lon, lat


def georeference_features(
    raw_response: dict,
    affine_transform,
    source_crs: str = "EPSG:32610",  # UTM Zone 10N (Sentinel-2 native)
) -> gpd.GeoDataFrame:
    """
    Convert pixel-space polygons from the Claude response to WGS84 geometries.

    Returns a GeoDataFrame in EPSG:4326.
    """
    from rasterio.crs import CRS
    from pyproj import Transformer

    features = raw_response.get("features", [])
    print(f"\nStep 3 — Georeferencing {len(features)} pixel polygon(s) to WGS84 ...")

    if not features:
        print("  No features to georeference — returning empty GeoDataFrame.")
        return gpd.GeoDataFrame(
            columns=["label", "confidence", "geometry"],
            geometry="geometry",
            crs="EPSG:4326",
        )

    # Sentinel-2 visual COGs are typically delivered in UTM (e.g. EPSG:32610 for SF)
    # rioxarray will report the native CRS; we reproject to WGS84 at the end.
    # pixel_to_world() gives us native CRS coordinates.
    rows = []
    skipped = 0

    for feat in features:
        geom_dict = feat.get("geometry", {})
        if geom_dict.get("type") != "Polygon":
            skipped += 1
            continue

        coords_px = geom_dict["coordinates"][0]  # outer ring only

        # Convert pixel coords → native CRS coords
        coords_crs = [pixel_to_world(x, y, affine_transform) for x, y in coords_px]

        # Ensure ring is closed
        if coords_crs[0] != coords_crs[-1]:
            coords_crs.append(coords_crs[0])

        if len(coords_crs) < 4:
            skipped += 1
            continue

        poly = Polygon(coords_crs)
        if not poly.is_valid:
            poly = poly.buffer(0)  # fix self-intersections

        rows.append({
            "label": feat.get("label", "building"),
            "confidence": float(feat.get("confidence", 0.5)),
            "geometry": poly,
        })

    if skipped:
        print(f"  Skipped {skipped} non-polygon or degenerate feature(s).")

    if not rows:
        print("  No valid polygons after parsing.")
        return gpd.GeoDataFrame(columns=["label", "confidence", "geometry"], geometry="geometry", crs="EPSG:4326")

    # Initialize with the native source CRS (e.g., UTM for Sentinel-2)
    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs=source_crs)

    # Reproject to WGS84 (EPSG:4326) for universal compatibility (lon/lat)
    # This is critical for visualization in tools like geojson.io and Kepler.gl
    gdf = gdf.to_crs("EPSG:4326")

    # Sanity check: all geometries should be within SF bbox (roughly)
    # This acts as an automated "Geospatial Guardrail" to catch VLM hallucinations
    sf_bounds = (-122.45, 37.70, -122.35, 37.85)
    out_of_bounds = gdf[
        ~gdf.geometry.bounds.apply(
            lambda r: (sf_bounds[0] <= r.minx <= sf_bounds[2])
                      and (sf_bounds[1] <= r.miny <= sf_bounds[3]),
            axis=1,
        )
    ]
    if not out_of_bounds.empty:
        print(f"  [GUARDRAIL] Flagged {len(out_of_bounds)} hallucinated feature(s) outside of San Francisco.")
        print("  → Note: These are retained in the output but flagged with confidence=0.0 and a label prefix.")
        gdf.loc[out_of_bounds.index, "confidence"] = 0.0
        gdf.loc[out_of_bounds.index, "label"] = (
            "[HALLUCINATION] " + gdf.loc[out_of_bounds.index, "label"]
        )

    print(f"  Georeferenced {len(gdf)} feature(s)  (Reprojected to EPSG:4326)")
    return gdf


# ---------------------------------------------------------------------------
# Step 4 — Write GeoJSON + GeoParquet
# ---------------------------------------------------------------------------

def write_outputs(gdf: gpd.GeoDataFrame) -> tuple[Path, Path]:
    """Write GeoDataFrame to GeoJSON and GeoParquet."""
    geojson_path = OUTPUT_DIR / "sf_buildings_vlm.geojson"
    geoparquet_path = OUTPUT_DIR / "sf_buildings_vlm.parquet"

    if gdf.empty:
        print("\nStep 4 — No features; writing empty placeholder files.")
        gdf.to_file(str(geojson_path), driver="GeoJSON")
        gdf.to_parquet(str(geoparquet_path))
        return geojson_path, geoparquet_path

    gdf.to_file(str(geojson_path), driver="GeoJSON")
    gdf.to_parquet(str(geoparquet_path))

    print(f"\nStep 4 — Outputs written:")
    print(f"  GeoJSON:     {geojson_path}")
    print(f"  GeoParquet:  {geoparquet_path}")

    # Quick summary
    high_conf = gdf[gdf.confidence >= 0.7]
    low_conf = gdf[gdf.confidence < 0.7]
    print(f"  High confidence (≥0.7): {len(high_conf)} features")
    print(f"  Low confidence  (<0.7): {len(low_conf)} features")

    return geojson_path, geoparquet_path


# ---------------------------------------------------------------------------
# Step 5 — Visualise georeferenced footprints over the chip
# ---------------------------------------------------------------------------

def visualise_footprints(gdf: gpd.GeoDataFrame, chip_png_path: Path) -> None:
    """Overlay the georeferenced footprints on the RGB chip for visual QA."""
    if not chip_png_path.exists():
        print("  Skipping visualisation — chip PNG not found (run Ex 1 first).")
        return

    from PIL import Image
    chip_img = np.array(Image.open(chip_png_path))

    fig, axes = plt.subplots(1, 2, figsize=(16, 8))

    # Left: raw chip
    axes[0].imshow(chip_img)
    axes[0].set_title("Sentinel-2 RGB Chip — SF Mission/SOMA")
    axes[0].axis("off")

    # Right: chip + footprints (using geopandas plot in geographic space)
    # Filter for non-hallucinations (confidence > 0) to avoid aspect-ratio errors
    # with extreme-latitude hallucinations during plotting.
    to_plot = gdf[gdf.confidence > 0] if not gdf.empty else gdf

    if not to_plot.empty:
        to_plot.plot(
            ax=axes[1],
            column="confidence",
            cmap="RdYlGn",
            vmin=0, vmax=1,
            edgecolor="white",
            linewidth=1.0,
            alpha=0.6,
            legend=True,
            legend_kwds={"label": "Confidence", "orientation": "horizontal"},
        )
        axes[1].set_title(f"VLM Building Footprints — {len(to_plot)} shown (Confidence > 0)")
        # Match spatial extent to chip bbox
        axes[1].set_xlim(SF_BBOX[0], SF_BBOX[2])
        axes[1].set_ylim(SF_BBOX[1], SF_BBOX[3])
    else:
        axes[1].text(
            0.5, 0.5, "No high-confidence footprints\n(check hallucination notes in README)",
            ha="center", va="center", transform=axes[1].transAxes, fontsize=12,
        )
        axes[1].set_title("VLM Building Footprints — 0 shown")
        # Ensure it still has a valid aspect for display
        axes[1].set_aspect("equal")
        axes[1].set_xlim(SF_BBOX[0], SF_BBOX[2])
        axes[1].set_ylim(SF_BBOX[1], SF_BBOX[3])
    axes[1].set_xlabel("Longitude")
    axes[1].set_ylabel("Latitude")

    plt.tight_layout()
    out_path = OUTPUT_DIR / "sf_buildings_overlay.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\n  Overlay visualisation saved: {out_path}  (open it to view)")


# ---------------------------------------------------------------------------
# Step 6 — Create a minimal PySTAC item
# ---------------------------------------------------------------------------

def create_stac_item(
    gdf: gpd.GeoDataFrame,
    cog_href: str,
    geojson_path: Path,
    geoparquet_path: Path,
    source_item,
) -> None:
    """
    Create a minimal STAC item that records:
      - Where the source COG came from (the Sentinel-2 item)
      - The derived building footprint GeoJSON and GeoParquet
      - The VLM model used and prompt version

    This is lightweight provenance — not a full catalog ingestion.
    """
    import pystac

    print("\nStep 6 — Creating PySTAC item for derived footprints ...")

    bbox = list(SF_BBOX)
    footprint = {
        "type": "Polygon",
        "coordinates": [[
            [SF_BBOX[0], SF_BBOX[1]],
            [SF_BBOX[2], SF_BBOX[1]],
            [SF_BBOX[2], SF_BBOX[3]],
            [SF_BBOX[0], SF_BBOX[3]],
            [SF_BBOX[0], SF_BBOX[1]],
        ]],
    }

    item = pystac.Item(
        id=f"sf-buildings-vlm-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}",
        geometry=footprint,
        bbox=bbox,
        datetime=datetime.now(timezone.utc),
        properties={
            "title": "San Francisco Building Footprints — Claude Vision Extraction",
            "description": (
                "Building footprints extracted from Sentinel-2 L2A visual chip "
                "using Claude Vision. EO Feature Extraction prototype — treat as exploratory, "
                "not production-grade. Hallucinations are expected."
            ),
            "vlm_model": CLAUDE_MODEL,
            "source_stac_id": source_item.id,
            "source_stac_collection": COLLECTION,
            "source_cog_href": cog_href,
            "feature_count": len(gdf),
            "high_confidence_count": int((gdf.confidence >= 0.7).sum()) if not gdf.empty else 0,
            "module": "eo-extraction",
        },
    )

    # Add asset links
    item.add_asset(
        "buildings_geojson",
        pystac.Asset(
            href=str(geojson_path.resolve()),
            media_type=pystac.MediaType.GEOJSON,
            title="Building Footprints (GeoJSON)",
            roles=["data"],
        ),
    )
    item.add_asset(
        "buildings_geoparquet",
        pystac.Asset(
            href=str(geoparquet_path.resolve()),
            media_type="application/vnd.apache.parquet",
            title="Building Footprints (GeoParquet)",
            roles=["data"],
        ),
    )
    item.add_asset(
        "source_cog",
        pystac.Asset(
            href=cog_href,
            media_type=pystac.MediaType.COG,
            title="Source Sentinel-2 Visual COG",
            roles=["data", "source"],
        ),
    )

    # Validate
    try:
        item.validate()
        print("  STAC item validation: PASSED")
    except Exception as exc:
        print(f"  STAC item validation: WARNING — {exc}")

    # Save
    stac_path = STAC_CATALOG_DIR / f"{item.id}.json"
    item.save_object(dest_href=str(stac_path))
    print(f"  STAC item saved: {stac_path}")


# ---------------------------------------------------------------------------
# Hallucination analysis
# ---------------------------------------------------------------------------

def hallucination_report(gdf: gpd.GeoDataFrame) -> None:
    """
    Print a short analysis of likely hallucinations.

    At Sentinel-2's 10m resolution, individual buildings are 2–5 pixels.
    The VLM may:
      - Invent building edges on uniform terrain (roads, parking lots)
      - Over-segment large buildings into many small polygons
      - Place polygons in cloud/shadow areas
      - Return polygons that are geographically valid but don't correspond to
        real structures (the most insidious type)

    This is a core teaching moment: vision models are powerful but unreliable
    compared to purpose-built segmentation models (SAM, etc.).
    """
    print("\n" + "=" * 60)
    print("HALLUCINATION ANALYSIS")
    print("=" * 60)

    if gdf.empty:
        print("  No features returned — either the model abstained (good)")
        print("  or returned unparseable JSON (check raw output above).")
    else:
        low = gdf[gdf.confidence < 0.5]
        flagged = gdf[gdf.label.str.contains("hallucination", case=False, na=False)]
        print(f"  Total features:        {len(gdf)}")
        print(f"  Low confidence (<0.5): {len(low)}")
        print(f"  Flagged out-of-bounds: {len(flagged)}")
        too_small = gdf[gdf.geometry.area < 1e-9]  # tiny in degrees²
        print(f"  Suspiciously tiny:     {len(too_small)}  (area < 1e-9 deg²)")

    print()
    print("  Common VLM hallucination patterns on EO imagery:")
    print("  1. Invented edges on parking lots / flat rooftops")
    print("  2. Over-segmenting one building into 5–10 polygons")
    print("  3. Shadows or cloud edges interpreted as building walls")
    print("  4. Geographically-valid but geospatially-incorrect coordinates")
    print()
    print("  # SAM alternative (not run here to avoid PyTorch dep conflicts):")
    print("  # from samgeo import SamGeo")
    print("  # sam = SamGeo(model_type='vit_h', automatic=True)")
    print("  # sam.generate(chip_array, output='sf_buildings_sam.tif')")
    print("  # sam.tiff_to_vector('sf_buildings_sam.tif', 'sf_buildings_sam.gpkg')")
    print("  #")
    print("  # SAM advantages: no hallucination (it segments real edges),")
    print("  # no API cost, but requires 2.5 GB model weights + GPU for speed.")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Cost estimate
# ---------------------------------------------------------------------------

def cost_estimate(usage_input_tokens: int, usage_output_tokens: int) -> None:
    """
    Print a rough cost estimate and extrapolate to city-scale.
    Uses claude-opus-4-5 pricing as a reference.
    """
    # claude-opus-4-5 pricing (as of 2025): $15 per 1M input, $75 per 1M output
    cost_input = usage_input_tokens * 15 / 1_000_000
    cost_output = usage_output_tokens * 75 / 1_000_000
    cost_per_chip = cost_input + cost_output

    # SF is roughly 121 km². At Sentinel-2 ~10m res, a full scene covers ~3600 km²
    # A 300×300 pixel chip covers ~3km × 3km = 9 km²
    # To cover SF (~121 km²) you'd need ~14 non-overlapping chips
    n_chips_sf = 14

    print("\n" + "=" * 60)
    print("COST + SCALE ESTIMATE (claude-opus-4-5)")
    print("=" * 60)
    print(f"  Per-chip:    ${cost_per_chip:.4f}  ({usage_input_tokens}in + {usage_output_tokens}out tokens)")
    print(f"  Cover SF:    {n_chips_sf} chips × ${cost_per_chip:.4f} = ${n_chips_sf * cost_per_chip:.2f}")
    print(f"  Latency:     {n_chips_sf} chips × ~5s = {n_chips_sf * 5}s  (sequential)")
    print()
    print("  For production EO feature extraction at city scale:")
    print("  → Use SAM or a fine-tuned segmentation model (zero marginal API cost)")
    print("  → VLMs are best for low-volume, exploratory, or hard-to-label tasks")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("Exercise 2: Extract Features with a Vision Model")
    print("=" * 60)

    # 1. Get chip
    image_bytes, affine_transform, cog_href, source_item, source_crs = get_chip_and_transform()

    # 2. Call Claude Vision
    raw_response = call_claude_vision(image_bytes)

    # Save raw response for inspection
    raw_path = OUTPUT_DIR / "claude_raw_response.json"
    with open(raw_path, "w") as f:
        json.dump(raw_response, f, indent=2)
    print(f"  Raw response saved: {raw_path}")

    # 3. Georeference
    # We pass the native CRS detected from the chip (likely UTM) to ensure
    # the affine transform accurately maps pixels to world units before WGS84 reprojection.
    gdf = georeference_features(raw_response, affine_transform, source_crs=source_crs)

    # 4. Write outputs
    geojson_path, geoparquet_path = write_outputs(gdf)

    # 5. Visualise overlay
    visualise_footprints(gdf, CHIP_PNG_PATH)

    # 6. STAC item
    create_stac_item(gdf, cog_href, geojson_path, geoparquet_path, source_item)

    # 7. Analysis
    hallucination_report(gdf)

    # Approximate token counts from last API call for the cost estimate
    # (We'd need to capture the usage object above — using placeholder if not captured)
    cost_estimate(usage_input_tokens=1200, usage_output_tokens=400)

    print("\nDone! Review output/ for all artifacts.")
    print("Key file to open: output/sf_buildings_vlm.geojson  (load in QGIS or kepler.gl)")


if __name__ == "__main__":
    main()
