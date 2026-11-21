"""
Scout ETL — Exercise 3: Build the STAC Catalog
========================================================

Reads the GeoParquet file produced by 02_build_sf_places.py and generates
a static STAC catalog describing it.

Why a STAC catalog?
  The catalog is the "schema registry" consumed by the NL-to-SQL LLM.
  Instead of hard-coding column names and category values into the prompt,
  the API route reads this JSON at request time. Updating the data and
  re-running this script is all that's needed to keep the LLM context current.

The catalog adds two Scout-specific STAC properties:
  scout:schema     — column name + type for every field in the GeoParquet
  scout:categories — the complete list of valid category values

Run:
    uv run python 03_build_stac_catalog.py
    (requires 02_build_sf_places.py to have been run first)

Output:
    output/stac/catalog.json
    output/stac/sf-places/collection.json
    output/stac/sf-places/sf-places-2026/sf-places-2026.json
"""

import json
import datetime
import duckdb
import pystac
from pathlib import Path
from shapely.geometry import box, mapping

# ---------------------------------------------------------------------------
# Configuration  (must match 02_build_geoparquet.py)
# ---------------------------------------------------------------------------

RELEASE       = "2026-01-21.0"
RELEASE_DATE  = datetime.datetime(2026, 1, 21, tzinfo=datetime.timezone.utc)

INPUT_FILE    = Path(__file__).parent / "output" / "sf_places.parquet"
STAC_DIR      = Path(__file__).parent / "output" / "stac"

# Human-readable descriptions for the schema (used in the LLM system prompt)
COLUMN_DESCRIPTIONS = {
    "id":       "Unique Overture Maps feature identifier (string)",
    "name":     "Display name of the place, e.g. 'Blue Bottle Coffee' (string)",
    "category": "Primary place category — see scout:categories for valid values (string)",
    "lat":      "Latitude of place centroid, WGS84 decimal degrees (double)",
    "lon":      "Longitude of place centroid, WGS84 decimal degrees (double)",
    "geometry": "WKB-encoded point geometry — use ST_GeomFromWKB(geometry) to cast (blob)",
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}\n"
            "Run 02_build_geoparquet.py first."
        )

    print("=" * 60)
    print("Scout ETL: Building STAC Catalog")
    print("=" * 60)
    print(f"  Input  : {INPUT_FILE}")
    print(f"  Output : {STAC_DIR}")
    print()

    STAC_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Step 1: Extract metadata from the GeoParquet
    # ------------------------------------------------------------------
    print("1/4  Reading metadata from GeoParquet...")
    con = duckdb.connect()

    stats = con.execute(f"""
        SELECT
            COUNT(*)                            AS row_count,
            COUNT(DISTINCT category)            AS category_count,
            MIN(lon)                            AS xmin,
            MAX(lon)                            AS xmax,
            MIN(lat)                            AS ymin,
            MAX(lat)                            AS ymax
        FROM read_parquet('{INPUT_FILE}')
    """).fetchone()

    row_count      = stats[0]
    bbox           = [float(stats[2]), float(stats[4]),
                      float(stats[3]), float(stats[5])]  # [xmin, ymin, xmax, ymax]

    # Full sorted list of category values — this is the LLM's closed vocabulary
    categories = con.execute(f"""
        SELECT DISTINCT category
        FROM read_parquet('{INPUT_FILE}')
        WHERE category IS NOT NULL
        ORDER BY category
    """).fetchall()
    category_list = [row[0] for row in categories]

    file_size_bytes = INPUT_FILE.stat().st_size

    print(f"     Row count   : {row_count:,}")
    print(f"     Categories  : {len(category_list)}")
    print(f"     Bbox        : {bbox}")
    print(f"     File size   : {file_size_bytes / (1024*1024):.2f} MB")

    con.close()

    # ------------------------------------------------------------------
    # Step 2: Build the STAC schema object
    # ------------------------------------------------------------------
    # This is the structured description the LLM will receive.
    # Every column name and type is explicit — no guessing.
    scout_schema = {
        col: desc
        for col, desc in COLUMN_DESCRIPTIONS.items()
    }

    # ------------------------------------------------------------------
    # Step 3: Assemble STAC objects using PySTAC
    # ------------------------------------------------------------------
    print("2/4  Building STAC catalog, collection, and item...")

    # --- Root Catalog ---
    catalog = pystac.Catalog(
        id="scout-data",
        description=(
            "Static STAC catalog for Scout — a cloud-native geospatial "
            "chat-to-map application. Contains GeoParquet partitions of "
            "Overture Maps places data processed for DuckDB-Wasm querying."
        ),
        title="Scout Data Catalog",
    )

    # --- Collection ---
    spatial_extent  = pystac.SpatialExtent(bboxes=[bbox])
    temporal_extent = pystac.TemporalExtent(
        intervals=[[RELEASE_DATE, None]]
    )

    collection = pystac.Collection(
        id="sf-places",
        description=(
            "San Francisco points of interest from Overture Maps "
            f"release {RELEASE}, filtered to confidence >= 0.7, "
            "spatially sorted by Hilbert curve, and compressed with ZSTD."
        ),
        title="SF Places (Overture Maps)",
        extent=pystac.Extent(
            spatial=spatial_extent,
            temporal=temporal_extent,
        ),
        license="ODbL-1.0",
    )
    catalog.add_child(collection)

    # --- Item ---
    # Fix type checker issue: box() expects 4 explicit floats
    minx, miny, maxx, maxy = bbox[0], bbox[1], bbox[2], bbox[3]
    item_geometry = mapping(box(minx, miny, maxx, maxy))  # GeoJSON polygon of bbox

    item = pystac.Item(
        id="sf-places-2026",
        geometry=item_geometry,
        bbox=bbox,
        datetime=RELEASE_DATE,
        properties={
            # Standard STAC fields
            "title":            "SF Places 2026 (Overture Maps)",
            "description":      (
                f"GeoParquet containing {row_count:,} San Francisco places "
                f"from Overture Maps release {RELEASE}."
            ),
            "overture:release": RELEASE,

            # Scout-specific properties consumed by the LLM prompt builder
            # (The NL-to-SQL logic reads these to construct the system prompt)
            "scout:row_count":  row_count,
            "scout:schema":     scout_schema,
            "scout:categories": category_list,
            "scout:table_name": "places",
            "scout:duckdb_notes": (
                "Load spatial extension before querying: LOAD spatial; "
                "Use ST_GeomFromWKB(geometry) to cast the geometry column. "
                "Use ST_DWithin(ST_Point(lon, lat), ST_Point(ref_lon, ref_lat), "
                "dist_degrees) for proximity queries. "
                "0.005 degrees ≈ 500m at SF latitude."
            ),
        },
    )

    # --- Asset: the GeoParquet file ---
    # href is relative — in production this would be an S3 URL.
    # For local development, the web app serves from public/data/.
    item.add_asset(
        "data",
        pystac.Asset(
            href="../sf_places.parquet",
            title="SF Places GeoParquet",
            media_type="application/vnd.apache.parquet",
            roles=["data"],
            extra_fields={
                "file:size":              file_size_bytes,
                "file:checksum":          None,  # populate with sha256 in production
            },
        ),
    )
    collection.add_item(item)

    # ------------------------------------------------------------------
    # Step 4: Normalize and save
    # ------------------------------------------------------------------
    print(f"3/4  Saving catalog to {STAC_DIR}...")
    catalog.normalize_and_save(
        str(STAC_DIR),
        catalog_type=pystac.CatalogType.SELF_CONTAINED,
    )

    # ------------------------------------------------------------------
    # Step 5: Validate
    # ------------------------------------------------------------------
    print("4/4  Validating...")
    try:
        catalog.validate_all()
        print("     STAC validation passed.")
    except Exception as exc:
        print(f"     Validation error: {exc}")

    # Print a summary of what the LLM will see from this catalog
    item_path = STAC_DIR / "sf-places" / "sf-places-2026" / "sf-places-2026.json"
    if item_path.exists():
        with open(item_path) as f:
            item_json = json.load(f)
        props = item_json.get("properties", {})
        print()
        print("  scout:categories (these go into the LLM prompt):")
        for cat in props.get("scout:categories", []):
            print(f"    - {cat}")

    # ------------------------------------------------------------------
    # Step 6: Verify by reading back the catalog and querying it
    # ------------------------------------------------------------------
    print()
    print("5/5  Verifying STAC catalog by reading it back...")
    try:
        # Read the catalog we just wrote
        loaded_catalog = pystac.Catalog.from_file(str(STAC_DIR / "catalog.json"))

        # Navigate to the item
        collections = list(loaded_catalog.get_collections())
        assert len(collections) == 1, f"Expected 1 collection, got {len(collections)}"

        sf_collection = collections[0]
        items = list(sf_collection.get_items())
        assert len(items) == 1, f"Expected 1 item, got {len(items)}"

        sf_item = items[0]

        # Verify critical properties exist
        props = sf_item.properties
        assert "scout:schema" in props, "Missing scout:schema property"
        assert "scout:categories" in props, "Missing scout:categories property"
        assert "scout:row_count" in props, "Missing scout:row_count property"

        # Verify the asset is present and has correct media type
        data_asset = sf_item.assets.get("data")
        assert data_asset is not None, "Missing 'data' asset"
        assert data_asset.media_type == "application/vnd.apache.parquet", \
            f"Wrong media type: {data_asset.media_type}"

        print(f"     ✓ Catalog structure valid")
        print(f"     ✓ Found {len(props['scout:categories'])} categories")
        print(f"     ✓ Schema has {len(props['scout:schema'])} columns")
        print(f"     ✓ Row count: {props['scout:row_count']:,}")
        print(f"     ✓ Data asset points to: {data_asset.href}")

    except Exception as e:
        print(f"     ✗ Verification failed: {e}")
        raise

    print()
    print("=" * 60)
    print("STAC catalog complete and verified.")
    print(f"Main item  : {item_path}")
    print("Next: NL-to-SQL Web GIS — build the semantic API route")
    print("=" * 60)
    print("=" * 60)


if __name__ == "__main__":
    main()
