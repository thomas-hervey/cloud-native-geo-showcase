"""
Scout ETL — Exercise 2: Build SF Places GeoParquet
====================================================
Thin wrapper around overture_etl.py for the SF places dataset.
See overture_etl.py for full documentation and configuration options.

Run:
    uv run python 02_build_sf_places.py

Output:
    output/sf_places.parquet   (~1-3 MB)
    public/data/sf_places.parquet  (copied for Next.js)

Next:
    uv run python 03_build_sf_buildings.py
"""

from pathlib import Path
from overture_etl import run_etl, SF_BBOX, DEFAULT_RELEASE

if __name__ == "__main__":
    run_etl(
        theme="places",
        release=DEFAULT_RELEASE,
        bbox=SF_BBOX,
        output=Path(__file__).parent / "output" / "sf_places.parquet",
        min_confidence=0.7,
        copy_to_public=True,
    )
