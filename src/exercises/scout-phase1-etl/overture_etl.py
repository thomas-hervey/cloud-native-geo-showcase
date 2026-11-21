"""
Overture Maps → GeoParquet ETL
================================
Generalized ETL for any Overture theme. Called by thin wrapper scripts.
Produces a Hilbert-sorted, ZSTD-compressed GeoParquet in the output dir
and optionally copies it to public/data/ for the Next.js app.

Usage (CLI):
    uv run python overture_etl.py --theme places
    uv run python overture_etl.py --theme buildings --copy-to-public

Programmatic:
    from overture_etl import run_etl, SF_BBOX, DEFAULT_RELEASE
    run_etl(theme="buildings", ...)
"""

import argparse
import shutil
import time
from pathlib import Path

import duckdb

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_RELEASE = "2026-01-21.0"

# San Francisco bounding box (WGS84)
SF_BBOX = {
    "xmin": -122.52, "xmax": -122.35,
    "ymin": 37.70,   "ymax": 37.84,
}

# Project root = 3 dirs up from this script (23-scout-etl → exercises → src → root)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
PUBLIC_DATA_DIR = PROJECT_ROOT / "public" / "data"

# ---------------------------------------------------------------------------
# Theme configurations
# ---------------------------------------------------------------------------

THEMES = {
    "places": {
        "s3_path": "theme=places/type=place/*",
        "output_file": "sf_places.parquet",
        "table_name": "sf_places",
        "description": "SF places (Overture Maps POIs)",
    },
    "buildings": {
        "s3_path": "theme=buildings/type=building/*",
        "output_file": "sf_buildings.parquet",
        "table_name": "sf_buildings",
        "description": "SF building footprints (Overture Maps)",
    },
}

# ---------------------------------------------------------------------------
# SQL builders per theme
# ---------------------------------------------------------------------------

def _places_sql(source_url: str, bbox: dict, min_confidence: float, table: str) -> str:
    return f"""
        CREATE OR REPLACE TABLE {table} AS
        SELECT
            id,
            names.primary                           AS name,
            basic_category                          AS category,
            ROUND(ST_Y(ST_Centroid(geometry)), 7)   AS lat,
            ROUND(ST_X(ST_Centroid(geometry)), 7)   AS lon,
            ST_AsWKB(geometry)                      AS geometry
        FROM read_parquet('{source_url}')
        WHERE
            bbox.xmin > {bbox['xmin']} AND bbox.xmax < {bbox['xmax']} AND
            bbox.ymin > {bbox['ymin']} AND bbox.ymax < {bbox['ymax']} AND
            names.primary   IS NOT NULL AND
            basic_category  IS NOT NULL AND
            confidence      >= {min_confidence}
        ORDER BY hilbert_encode([lon, lat]::DOUBLE[2])
    """


def _buildings_sql(source_url: str, bbox: dict, table: str) -> str:
    return f"""
        CREATE OR REPLACE TABLE {table} AS
        SELECT
            id,
            height                                  AS height,
            num_floors                              AS floors,
            class                                   AS use_class,
            ROUND(ST_Y(ST_Centroid(geometry)), 7)   AS lat,
            ROUND(ST_X(ST_Centroid(geometry)), 7)   AS lon,
            ST_AsWKB(geometry)                      AS geometry
        FROM read_parquet('{source_url}')
        WHERE
            bbox.xmin > {bbox['xmin']} AND bbox.xmax < {bbox['xmax']} AND
            bbox.ymin > {bbox['ymin']} AND bbox.ymax < {bbox['ymax']}
        ORDER BY hilbert_encode([lon, lat]::DOUBLE[2])
    """


def _count_sql(source_url: str, bbox: dict, theme: str, min_confidence: float) -> str:
    base = f"""
        SELECT COUNT(*) AS n FROM read_parquet('{source_url}')
        WHERE
            bbox.xmin > {bbox['xmin']} AND bbox.xmax < {bbox['xmax']} AND
            bbox.ymin > {bbox['ymin']} AND bbox.ymax < {bbox['ymax']}
    """
    if theme == "places":
        base += f"""
            AND names.primary IS NOT NULL
            AND basic_category IS NOT NULL
            AND confidence >= {min_confidence}
        """
    return base


def _verify_sql(output_file: Path, theme: str) -> str:
    extra = ", COUNT(DISTINCT category) AS cat_count" if theme == "places" else \
            ", AVG(height) AS avg_height, COUNT(height) AS with_height"
    return f"""
        SELECT COUNT(*) AS row_count{extra},
               MIN(lon) AS lon_min, MAX(lon) AS lon_max,
               MIN(lat) AS lat_min, MAX(lat) AS lat_max
        FROM read_parquet('{output_file}')
    """

# ---------------------------------------------------------------------------
# Main ETL function
# ---------------------------------------------------------------------------

def run_etl(
    theme: str,
    release: str = DEFAULT_RELEASE,
    bbox: dict = SF_BBOX,
    output: "Path | None" = None,
    min_confidence: float = 0.7,
    copy_to_public: bool = False,
) -> Path:
    """
    Run the Overture → GeoParquet ETL for the given theme.

    Returns the path to the written parquet file.
    """
    if theme not in THEMES:
        raise ValueError(f"Unknown theme '{theme}'. Choose: {list(THEMES)}")

    cfg = THEMES[theme]
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    if output is None:
        output = output_dir / cfg["output_file"]

    source_url = (
        f"s3://overturemaps-us-west-2/release/{release}/{cfg['s3_path']}"
    )
    table = cfg["table_name"]

    print("=" * 64)
    print(f"Overture ETL: {cfg['description']}")
    print("=" * 64)
    print(f"  Theme    : {theme}")
    print(f"  Release  : {release}")
    print(f"  Bbox     : ({bbox['xmin']}, {bbox['ymin']}) → ({bbox['xmax']}, {bbox['ymax']})")
    print(f"  Output   : {output}")
    print()

    con = duckdb.connect()

    # 1. Extensions
    print("1/5  Loading extensions...")
    con.execute("INSTALL httpfs;   LOAD httpfs;")
    con.execute("INSTALL spatial;  LOAD spatial;")
    con.execute("INSTALL lindel FROM community; LOAD lindel;")
    # Overture S3 is publicly readable — no credentials needed
    con.execute("SET s3_region='us-west-2';")
    con.execute("SET s3_access_key_id='';")
    con.execute("SET s3_secret_access_key='';")

    # 2. Count
    print("2/5  Counting records in bbox (streaming from S3)...")
    t0 = time.time()
    n = con.execute(_count_sql(source_url, bbox, theme, min_confidence)).fetchone()[0]
    print(f"     → {n:,} records pass filter  ({time.time() - t0:.1f}s)")
    if n == 0:
        raise RuntimeError("No records returned — check bbox and S3 path.")

    # 3. Build
    print("3/5  Fetching, flattening, and Hilbert-sorting...")
    t0 = time.time()
    if theme == "places":
        build_sql = _places_sql(source_url, bbox, min_confidence, table)
    else:
        build_sql = _buildings_sql(source_url, bbox, table)
    con.execute(build_sql)
    print(f"     → Done  ({time.time() - t0:.1f}s)")

    # 4. Write
    print(f"4/5  Writing GeoParquet → {output} ...")
    t0 = time.time()
    con.execute(f"""
        COPY {table} TO '{output}'
        (FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 5000)
    """)
    size_mb = output.stat().st_size / (1024 * 1024)
    print(f"     → {size_mb:.2f} MB  ({time.time() - t0:.1f}s)")

    # 5. Verify
    print("5/5  Verifying output...")
    row = con.execute(_verify_sql(output, theme)).fetchone()
    print(f"     Row count  : {row[0]:,}")
    if theme == "places":
        print(f"     Categories : {row[1]}")
    else:
        print(f"     Avg height : {row[1]:.1f}m  ({row[2]:,} buildings with height data)")
    print(f"     Lon range  : {row[-4]:.4f} → {row[-3]:.4f}")
    print(f"     Lat range  : {row[-2]:.4f} → {row[-1]:.4f}")

    con.close()

    # 6. Copy to public/data/
    if copy_to_public:
        PUBLIC_DATA_DIR.mkdir(parents=True, exist_ok=True)
        dest = PUBLIC_DATA_DIR / cfg["output_file"]
        shutil.copy2(output, dest)
        print(f"\n  Copied → {dest}")

    print()
    print("=" * 64)
    print(f"ETL complete: {output}")
    print("=" * 64)

    return output


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _parse_args():
    p = argparse.ArgumentParser(description="Overture Maps → GeoParquet ETL")
    p.add_argument("--theme", required=True, choices=list(THEMES),
                   help="Overture theme to fetch")
    p.add_argument("--release", default=DEFAULT_RELEASE,
                   help=f"Overture release tag (default: {DEFAULT_RELEASE})")
    p.add_argument("--bbox", default=None,
                   help="Bounding box as 'xmin,ymin,xmax,ymax' (default: SF)")
    p.add_argument("--output", default=None,
                   help="Output parquet path (default: output/<theme>.parquet)")
    p.add_argument("--min-confidence", type=float, default=0.7,
                   help="Min confidence for places (default: 0.7)")
    p.add_argument("--copy-to-public", action="store_true",
                   help="Copy output to public/data/ after writing")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    bbox = SF_BBOX
    if args.bbox:
        parts = [float(x) for x in args.bbox.split(",")]
        bbox = {"xmin": parts[0], "ymin": parts[1], "xmax": parts[2], "ymax": parts[3]}

    run_etl(
        theme=args.theme,
        release=args.release,
        bbox=bbox,
        output=Path(args.output) if args.output else None,
        min_confidence=args.min_confidence,
        copy_to_public=args.copy_to_public,
    )
