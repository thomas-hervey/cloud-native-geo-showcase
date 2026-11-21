"""
Exercise 2: Multi-Format I/O
=============================
Motivating question: Can DuckDB read any geospatial format, and what does
the performance and size difference between GeoJSON and GeoParquet look like?

Run from src/exercises/:
    uv run python duckdb-spatial/02_multiformat_io.py

Output:
    duckdb-spatial/output/02_format_benchmark.png
    duckdb-spatial/output/sf_restaurants.parquet
"""
import os
import sys
import time
import duckdb
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt

PLACES_PARQUET = "scout-etl/output/sf_places.parquet"
NEIGHBORHOODS_GEOJSON = "spatial-eval/data/Analysis_Neighborhoods_20260309.geojson"
COUNTRIES_GPKG = "legacy-ingest/data/countries.gpkg"
OUTPUT_DIR = "duckdb-spatial/output"
RESTAURANTS_OUT = f"{OUTPUT_DIR}/sf_restaurants.parquet"
TMP_GEOJSON = f"{OUTPUT_DIR}/sf_places_tmp.geojson"


def best_of(con, sql, runs=5):
    """Return the best (minimum) query time over `runs` executions."""
    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        con.execute(sql).fetchone()
        times.append(time.perf_counter() - t0)
    return min(times)


def mb(path):
    return os.path.getsize(path) / 1024 ** 2


def main():
    missing = [p for p in [PLACES_PARQUET, NEIGHBORHOODS_GEOJSON, COUNTRIES_GPKG] if not os.path.exists(p)]
    if missing:
        for p in missing:
            print(f"  Missing: {p}")
        sys.exit("Run this script from src/exercises/ — input files not found")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")

    # ── 1. Read formats ────────────────────────────────────────────────────────
    print("=== 1. READING THREE FORMATS ===\n")

    # GeoJSON via ST_Read (GDAL backend)
    print("--- GeoJSON (ST_Read / GDAL) ---")
    schema_geojson = con.execute(
        f"DESCRIBE SELECT * FROM ST_Read('{NEIGHBORHOODS_GEOJSON}')"
    ).df()
    n_geojson = con.execute(
        f"SELECT COUNT(*) FROM ST_Read('{NEIGHBORHOODS_GEOJSON}')"
    ).fetchone()[0]
    t_geojson_nbhoods = best_of(con, f"SELECT COUNT(*) FROM ST_Read('{NEIGHBORHOODS_GEOJSON}')")
    print(f"  {n_geojson} rows in {t_geojson_nbhoods * 1000:.1f}ms")
    print(schema_geojson[['column_name', 'column_type']].to_string(index=False))

    # GeoParquet via read_parquet
    print("\n--- GeoParquet (read_parquet) ---")
    schema_parquet = con.execute(
        f"DESCRIBE SELECT * FROM read_parquet('{PLACES_PARQUET}')"
    ).df()
    n_parquet = con.execute(
        f"SELECT COUNT(*) FROM read_parquet('{PLACES_PARQUET}')"
    ).fetchone()[0]
    t_parquet_places = best_of(con, f"SELECT COUNT(*) FROM read_parquet('{PLACES_PARQUET}')")
    print(f"  {n_parquet:,} rows in {t_parquet_places * 1000:.1f}ms")
    print(schema_parquet[['column_name', 'column_type']].to_string(index=False))

    # GeoPackage via ST_Read (GDAL)
    print("\n--- GeoPackage (ST_Read / GDAL) ---")
    schema_gpkg = con.execute(
        f"DESCRIBE SELECT * FROM ST_Read('{COUNTRIES_GPKG}')"
    ).df()
    n_gpkg = con.execute(
        f"SELECT COUNT(*) FROM ST_Read('{COUNTRIES_GPKG}')"
    ).fetchone()[0]
    t_gpkg = best_of(con, f"SELECT COUNT(*) FROM ST_Read('{COUNTRIES_GPKG}')")
    print(f"  {n_gpkg} rows in {t_gpkg * 1000:.1f}ms")
    print(schema_gpkg[['column_name', 'column_type']].to_string(index=False))

    # ── 2. CRS inspection ─────────────────────────────────────────────────────
    print("\n=== CRS Inspection (ST_CRS) ===")

    # Register views so we can reference them by name
    con.execute(f"CREATE OR REPLACE VIEW neighborhoods AS SELECT * FROM ST_Read('{NEIGHBORHOODS_GEOJSON}')")
    con.execute(f"CREATE OR REPLACE VIEW places AS SELECT * FROM read_parquet('{PLACES_PARQUET}')")
    con.execute(f"CREATE OR REPLACE VIEW countries AS SELECT * FROM ST_Read('{COUNTRIES_GPKG}')")

    # DuckDB 1.5 exposes ST_CRS() (returns e.g. "EPSG:4326"); parse SRID from it
    def srid_from_crs(crs_str: str) -> int:
        """Extract numeric SRID from a CRS authority string like 'EPSG:4326'."""
        if crs_str and ":" in crs_str:
            return int(crs_str.split(":")[-1])
        return 0

    crs_geojson = srid_from_crs(con.execute("SELECT ST_CRS(geom)::VARCHAR AS crs FROM neighborhoods LIMIT 1").fetchone()[0])
    crs_parquet = srid_from_crs(con.execute("SELECT ST_CRS(geometry::GEOMETRY)::VARCHAR AS crs FROM places LIMIT 1").fetchone()[0])
    crs_gpkg = srid_from_crs(con.execute("SELECT ST_CRS(geom)::VARCHAR AS crs FROM countries LIMIT 1").fetchone()[0])
    print(f"  GeoJSON (neighborhoods):  SRID = {crs_geojson}")
    print(f"  GeoParquet (places):      SRID = {crs_parquet}")
    print(f"  GeoPackage (countries):   SRID = {crs_gpkg}")

    # ── 3. The benchmark: GeoJSON vs GeoParquet at scale ─────────────────────
    print("\n=== 3. FORMAT BENCHMARK: GeoJSON vs GeoParquet (42K places) ===")
    print("  Writing places as GeoJSON (slow by design — this is the point)...")

    places_gdf = gpd.read_parquet(PLACES_PARQUET)
    t0 = time.perf_counter()
    places_gdf.to_file(TMP_GEOJSON, driver='GeoJSON')
    t_write = time.perf_counter() - t0
    print(f"  Write time: {t_write:.3f}s (slow by design — JSON serialization of 42K features)")

    geojson_size_mb = mb(TMP_GEOJSON)
    parquet_size_mb = mb(PLACES_PARQUET)
    gpkg_mb = mb(COUNTRIES_GPKG)
    t_read_geojson = best_of(con, f"SELECT COUNT(*) FROM ST_Read('{TMP_GEOJSON}')")
    t_read_parquet = best_of(con, f"SELECT COUNT(*) FROM read_parquet('{PLACES_PARQUET}')")

    print(f"\n  File size:  GeoJSON = {geojson_size_mb:.1f} MB | GeoParquet = {parquet_size_mb:.1f} MB")
    print(f"  Size ratio: GeoParquet is {geojson_size_mb / parquet_size_mb:.1f}× smaller")
    print(f"  Read time:  GeoJSON = {t_read_geojson * 1000:.0f}ms | GeoParquet = {t_read_parquet * 1000:.1f}ms")
    print(f"  Read ratio: GeoParquet is {t_read_geojson / t_read_parquet:.0f}× faster")

    # ── 4. Write filtered GeoParquet ──────────────────────────────────────────
    print("\n=== 4. WRITE FILTERED GEOPARQUET ===")
    con.execute(f"""
        COPY (
            SELECT id, name, category, lat, lon, geometry
            FROM read_parquet('{PLACES_PARQUET}')
            WHERE category = 'restaurant'
        ) TO '{RESTAURANTS_OUT}' (FORMAT PARQUET)
    """)
    n_rest = con.execute(
        f"SELECT COUNT(*) FROM read_parquet('{RESTAURANTS_OUT}')"
    ).fetchone()[0]
    print(f"  Wrote {n_rest:,} restaurants → {RESTAURANTS_OUT} ({mb(RESTAURANTS_OUT):.2f} MB)")

    # ── 5. Round-trip to GeoPandas ────────────────────────────────────────────
    print("\n=== GeoPandas Round-Trip (WKB) ===")
    df = pd.read_parquet(RESTAURANTS_OUT)
    rest_gdf = gpd.GeoDataFrame(
        df.drop(columns=["geometry"]),
        geometry=gpd.GeoSeries.from_wkb(df["geometry"].apply(bytes)),
        crs="EPSG:4326",
    )
    print(f"  Loaded {len(rest_gdf):,} restaurants via from_wkb")
    print(f"  CRS: {rest_gdf.crs}")
    print(f"  Sample:\n{rest_gdf[['name', 'geometry']].head(3).to_string()}")

    # ── Visualization ─────────────────────────────────────────────────────────
    print("\n=== GENERATING VISUALIZATION ===")

    labels = ["GeoJSON\n(neighborhoods)", "GeoParquet\n(places)", "GeoPackage\n(countries)"]
    sizes_mb = [geojson_size_mb, parquet_size_mb, gpkg_mb]
    times_s = [t_read_geojson, t_read_parquet, t_gpkg]
    colors = ["#e07b39", "#4c9be8", "#6abf69"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    bars0 = ax1.bar(labels, sizes_mb, color=colors, edgecolor='black', linewidth=0.8)
    for bar, val in zip(bars0, sizes_mb):
        ax1.text(
            bar.get_x() + bar.get_width() / 2, bar.get_height() + max(sizes_mb) * 0.02,
            f'{val:.1f} MB', ha='center', va='bottom', fontweight='bold', fontsize=11,
        )
    ax1.set_title("File Size by Format", fontweight='bold')
    ax1.set_ylabel("Size (MB)")
    ax1.set_ylim(0, max(sizes_mb) * 1.3)
    ax1.grid(axis='y', alpha=0.3)

    bars1 = ax2.bar(labels, times_s, color=colors, edgecolor='black', linewidth=0.8)
    for bar, val in zip(bars1, times_s):
        label = f'{val * 1000:.0f}ms' if val < 1 else f'{val:.2f}s'
        ax2.text(
            bar.get_x() + bar.get_width() / 2, bar.get_height() + max(times_s) * 0.02,
            label, ha='center', va='bottom', fontweight='bold', fontsize=11,
        )
    ax2.set_title("Read Time by Format", fontweight='bold')
    ax2.set_ylabel("Time (seconds)")
    ax2.set_ylim(0, max(times_s) * 1.3)
    ax2.grid(axis='y', alpha=0.3)

    fig.suptitle("DuckDB Multi-Format I/O Benchmark", fontsize=14, fontweight='bold')
    fig.text(0.5, -0.02, "Note: different datasets — sizes/times reflect both format and dataset scale",
             ha='center', fontsize=9, style='italic', color='gray')
    plt.tight_layout()
    out = f"{OUTPUT_DIR}/02_format_benchmark.png"
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()

    os.remove(TMP_GEOJSON)  # temp file
    print(f"Saved: {out}")
    print(f"Saved: {RESTAURANTS_OUT}")

    con.close()


if __name__ == "__main__":
    main()
