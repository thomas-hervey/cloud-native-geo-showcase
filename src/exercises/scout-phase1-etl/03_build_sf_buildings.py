"""
Scout ETL — Exercise 3: Build SF Buildings GeoParquet
======================================================
Thin wrapper around overture_etl.py for the SF buildings dataset.
Fetches ~220,000 building footprints from Overture Maps for San Francisco.
Expect this to take 2-5 minutes — it streams from S3.

Run:
    uv run python 03_build_sf_buildings.py

Output:
    output/sf_buildings.parquet   (~8-15 MB)
    public/data/sf_buildings.parquet  (copied for Next.js)

Next:
    uv run python 04_build_stac_catalog.py
"""

from pathlib import Path
from overture_etl import run_etl, SF_BBOX, DEFAULT_RELEASE

if __name__ == "__main__":
    run_etl(
        theme="buildings",
        release=DEFAULT_RELEASE,
        bbox=SF_BBOX,
        output=Path(__file__).parent / "output" / "sf_buildings.parquet",
        copy_to_public=True,
    )
