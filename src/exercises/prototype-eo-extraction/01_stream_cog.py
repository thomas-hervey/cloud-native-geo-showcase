"""
Exercise 1: Stream COG Imagery
==========================================
Stream a Cloud-Optimized GeoTIFF from AWS Open Data using HTTP range requests.
We search for a Sentinel-2 L2A scene over San Francisco via the Element 84
Earth Search STAC API, then read just a small spatial window (a few hundred
pixels) without downloading the whole ~1 GB file.

Key concepts:
  - STAC API search to discover public COGs
  - rioxarray.open_rasterio() with fsspec for cloud-native reads
  - COG overview levels for fast thumbnails
  - Estimating uncompressed pixel data size for the chip vs. the full file size
    (a proxy for understanding COG range-request efficiency; actual HTTP bytes
    transferred will be smaller due to COG tile compression)

Run from src/exercises/:
    uv run python eo-extraction/01_stream_cog.py
"""

import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend — saves to file, no display window needed
import matplotlib.pyplot as plt
import numpy as np
import requests
from pystac_client import Client

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# San Francisco bounding box — Mission/SOMA area.
# Dense urban fabric, clear building footprints, good for Exercise 2 later.
# Format: [west, south, east, north] in WGS84
SF_BBOX = [-122.42, 37.77, -122.39, 37.80]

# Earth Search v1 — free, no auth, backed by AWS Open Data
STAC_API_URL = "https://earth-search.aws.element84.com/v1"
COLLECTION = "sentinel-2-l2a"

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Step 1 — Search STAC for a low-cloud Sentinel-2 scene over SF
# ---------------------------------------------------------------------------

def search_sentinel2(bbox: list[float], max_cloud_cover: int = 15) -> dict:
    """
    Search the Element 84 Earth Search STAC API for a recent Sentinel-2 L2A
    scene over the given bounding box with low cloud cover.

    Returns the first matching STAC item as a dict.
    """
    print(f"Searching Earth Search for Sentinel-2 over bbox={bbox} ...")
    catalog = Client.open(STAC_API_URL)

    results = catalog.search(
        collections=[COLLECTION],
        bbox=bbox,
        query={"eo:cloud_cover": {"lt": max_cloud_cover}},
        max_items=5,
    )

    items = list(results.items())
    if not items:
        raise RuntimeError(
            f"No Sentinel-2 scenes found for bbox={bbox} with cloud cover < {max_cloud_cover}%. "
            "Try increasing max_cloud_cover or widening the bbox."
        )

    item = items[0]
    cloud_pct = item.properties.get("eo:cloud_cover", "?")
    print(f"  Found: {item.id}")
    print(f"  Date:  {item.datetime.date()}")
    print(f"  Cloud: {cloud_pct}%")
    return item


# ---------------------------------------------------------------------------
# Step 2 — Inspect the COG asset for the visual (RGB) band
# ---------------------------------------------------------------------------

def get_visual_href(item) -> tuple[str, float]:
    """
    Return the HTTPS URL for the visual (true-colour RGB) COG asset and the
    approximate file size in MB as reported by a HEAD request.

    The 'visual' asset is a 3-band uint8 RGB COG — perfect for visualisation
    and for passing directly to Claude Vision in Exercise 2.
    """
    asset = item.assets.get("visual")
    if asset is None:
        # Fallback: B04 (Red) if visual isn't available
        asset = item.assets.get("B04") or item.assets.get("red")
    if asset is None:
        raise KeyError(f"No 'visual' or 'B04' asset in item {item.id}. Available: {list(item.assets.keys())}")

    href = asset.href
    print(f"\nCOG asset URL:\n  {href}")

    # HEAD request — get the full file size without downloading it
    try:
        head = requests.head(href, allow_redirects=True, timeout=10)
        head.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Failed to retrieve COG header for {href}") from exc
    full_size_bytes = int(head.headers.get("Content-Length", 0))
    full_size_mb = full_size_bytes / 1_048_576
    print(f"  Full COG size: {full_size_mb:.1f} MB ({full_size_bytes:,} bytes)")

    return href, full_size_mb


# ---------------------------------------------------------------------------
# Step 3 — Read a spatial window via COG range requests
# ---------------------------------------------------------------------------

def stream_chip(href: str, bbox: list[float]) -> tuple:
    """
    Read a spatial window from the COG using rioxarray + fsspec.
    Returns (chip_array, profile_dict, elapsed_seconds).

    rioxarray handles the HTTP range requests transparently — it only fetches
    the tiles that overlap our bounding box, not the whole file.
    """
    import rioxarray  # noqa: F401 — registers the .rio accessor on xarray

    import xarray as xr

    print(f"\nReading chip from COG (bbox={bbox}) ...")
    t0 = time.perf_counter()

    # open_rasterio lazily opens the COG — no data transferred yet
    da = rioxarray.open_rasterio(
        href,
        parse_coordinates=True,
        chunks={},         # enables dask (lazy evaluation)
        lock=False,        # allow concurrent tile reads
    )

    # Clip to our bounding box — this is where the range requests fire
    chip = da.rio.clip_box(
        minx=bbox[0], miny=bbox[1],
        maxx=bbox[2], maxy=bbox[3],
        crs="EPSG:4326",
    )

    # .values triggers actual HTTP fetch
    data = chip.values
    elapsed = time.perf_counter() - t0

    print(f"  Chip shape: {data.shape}  (bands × rows × cols)")
    print(f"  dtype:      {data.dtype}")
    print(f"  CRS:        {chip.rio.crs}")
    print(f"  Transform:  {chip.rio.transform()}")
    print(f"  Fetched in: {elapsed:.2f}s")

    return chip, data, elapsed


# ---------------------------------------------------------------------------
# Step 4 — Visualise and save the RGB chip
# ---------------------------------------------------------------------------

def visualise_chip(data: np.ndarray, chip, output_path: Path) -> None:
    """
    Display the RGB chip with matplotlib and save to disk.
    """
    # Sentinel-2 visual asset is uint8 0–255, 3 bands (RGB)
    if data.shape[0] == 3:
        rgb = np.moveaxis(data, 0, -1)  # (3, H, W) → (H, W, 3)
        cmap = None
        title = "Sentinel-2 RGB Chip — San Francisco (Mission/SOMA)"
    else:
        # Single band (e.g. B04) — show as greyscale
        rgb = data[0]
        cmap = "gray"
        title = f"Sentinel-2 Band Chip — San Francisco (band shape: {data.shape})"

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.imshow(rgb, cmap=cmap)
    ax.set_title(title, fontsize=11)
    ax.axis("off")

    # Annotate with transform info
    t = chip.rio.transform()
    res_x = abs(t.a)
    res_y = abs(t.e)

    # Determine units from CRS: degrees for geographic, meters otherwise
    crs = getattr(chip.rio, "crs", None)
    unit = "°" if (crs is not None and getattr(crs, "is_geographic", False)) else "m"

    ax.set_xlabel(
        f"res: {res_x:.6f} {unit} × {res_y:.6f} {unit} per pixel  |  "
        f"size: {data.shape[-1]}×{data.shape[-2]} px",
        fontsize=8,
    )

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\n  Chip saved: {output_path}  (open it to view)")


# ---------------------------------------------------------------------------
# Step 5 — Bandwidth comparison
# ---------------------------------------------------------------------------

def bandwidth_report(full_size_mb: float, elapsed_s: float, chip_shape: tuple) -> None:
    """
    Print a human-readable bandwidth comparison:
    uncompressed chip pixel size (estimate) vs. the full COG file size on disk.

    Note: this is an upper-bound approximation of the data read, not a
    measurement of actual HTTP bytes transferred.  COG tiles are stored
    compressed (DEFLATE/LZW/WebP), so the real wire traffic is smaller.
    """
    total_pixels = chip_shape[1] * chip_shape[2]     # H × W
    bands = chip_shape[0]

    # Rough estimate: each pixel = bands × 1 byte (uint8 visual) or 2 bytes (uint16 bands)
    bytes_per_pixel = 1 if bands == 3 else 2          # visual=uint8, spectral=uint16
    chip_bytes_approx = total_pixels * bands * bytes_per_pixel
    chip_mb_approx = chip_bytes_approx / 1_048_576

    print("\n" + "=" * 60)
    print("BANDWIDTH COMPARISON (approximate)")
    print("=" * 60)
    print(f"  Full COG file size:               {full_size_mb:>8.1f} MB")
    print(f"  Chip pixels (uncompressed est.):  ~{chip_mb_approx:>7.2f} MB")
    if full_size_mb > 0:
        pct = chip_mb_approx / full_size_mb * 100
        print(f"  Chip / full-file ratio:           {pct:>7.1f}%")
    print(f"  Chip fetch time:                  {elapsed_s:>8.2f}s")
    print()
    print("  Note: actual HTTP bytes transferred are lower — COG tiles")
    print("  are compressed on disk.  This estimate gives an upper bound.")
    print()
    print("  COG summary:")
    print("  - The COG stores the image in tiled strips + overviews")
    print("  - rioxarray sends HTTP Range: bytes=... requests")
    print("  - Only the tiles that overlap our bbox are fetched")
    print("  - For a 1 GB S2 scene, we read < 1% of the data")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Bonus — NDVI from the red + NIR bands
# ---------------------------------------------------------------------------

def compute_ndvi_chip(item, bbox: list[float]) -> None:
    """
    Bonus section: read the Red (B04) and NIR (B08) bands separately and
    compute NDVI = (NIR - Red) / (NIR + Red).

    NDVI ranges from -1 (water/non-veg) to +1 (dense vegetation).
    In urban SF, you'll see near-zero values over pavement and the
    positive spike over parks like Dolores.
    """
    import rioxarray  # noqa: F401
    import xarray as xr

    print("\n--- Bonus: NDVI chip ---")

    b04_href = item.assets.get("B04") or item.assets.get("red")
    b08_href = item.assets.get("B08") or item.assets.get("nir")

    if b04_href is None or b08_href is None:
        print("  Skipping NDVI — B04/B08 assets not available in this item.")
        return

    def read_band(href: str) -> np.ndarray:
        da = rioxarray.open_rasterio(href, parse_coordinates=True, lock=False)
        chip = da.rio.clip_box(
            minx=bbox[0], miny=bbox[1],
            maxx=bbox[2], maxy=bbox[3],
            crs="EPSG:4326",
        )
        return chip.values[0].astype(np.float32)

    red = read_band(b04_href.href)
    nir = read_band(b08_href.href)

    # Avoid divide-by-zero
    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = np.where(
            (nir + red) == 0,
            np.nan,
            (nir - red) / (nir + red),
        )

    ndvi_path = OUTPUT_DIR / "sf_ndvi_chip.png"
    fig, ax = plt.subplots(figsize=(8, 8))
    im = ax.imshow(ndvi, cmap="RdYlGn", vmin=-0.2, vmax=0.5)
    ax.set_title("NDVI — San Francisco (Mission/SOMA)\n-1=water/urban, +1=dense vegetation")
    ax.axis("off")
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="NDVI")
    plt.tight_layout()
    plt.savefig(ndvi_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  NDVI chip saved: {ndvi_path}  (open it to view)")
    print(f"  NDVI range: {np.nanmin(ndvi):.3f} \u2192 {np.nanmax(ndvi):.3f}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("Exercise 1: Stream COG Imagery")
    print("=" * 60)

    # 1. Find a Sentinel-2 scene
    item = search_sentinel2(SF_BBOX, max_cloud_cover=20)

    # 2. Get the visual COG URL + full file size
    cog_href, full_size_mb = get_visual_href(item)

    # 3. Stream just the chip we need
    chip, data, elapsed = stream_chip(cog_href, SF_BBOX)

    # 4. Visualise
    out_png = OUTPUT_DIR / "sf_rgb_chip.png"
    visualise_chip(data, chip, out_png)

    # 5. Bandwidth report
    bandwidth_report(full_size_mb, elapsed, data.shape)

    # Bonus: NDVI
    compute_ndvi_chip(item, SF_BBOX)

    print("\nDone! Check output/ for the saved chips.")
    print("Next: run 02_vision_inference.py to extract building footprints.")


if __name__ == "__main__":
    main()
