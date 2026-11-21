"""
Exercise 3: Indexing & Performance
====================================
Motivating question: Does a spatial index actually matter, and how does
the two-stage filter pattern work in practice?

This exercise demonstrates three DuckDB spatial performance patterns:
  1. Columnar predicate pushdown (GeoParquet vs GeoJSON)
  2. R-tree spatial index (point-in-polygon join)
  3. Two-stage filter (bbox pre-filter + precise ST_DWithin)

Run from src/exercises/:
    uv run python duckdb-spatial/03_indexing_and_performance.py

Output:
    duckdb-spatial/output/03_benchmark_results.png
"""
import os
import sys
import time
import duckdb
import geopandas as gpd
import matplotlib.pyplot as plt

PLACES_PARQUET = "scout-etl/output/sf_places.parquet"
BUILDINGS_PARQUET = "scout-etl/output/sf_buildings.parquet"
OUTPUT_DIR = "duckdb-spatial/output"
TMP_GEOJSON = f"{OUTPUT_DIR}/places_bench_tmp.geojson"

# SF City Hall for the two-stage filter demo
CITY_HALL_LON, CITY_HALL_LAT = -122.4194, 37.7793
RADIUS_DEG = 0.018  # ~2km at SF latitude


def best_of(con, sql, runs=5):
    """Return the best (minimum) query time over `runs` executions."""
    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        con.execute(sql).fetchone()
        times.append(time.perf_counter() - t0)
    return min(times)


def main():
    # Preflight check
    missing = [p for p in [PLACES_PARQUET, BUILDINGS_PARQUET] if not os.path.exists(p)]
    if missing:
        for p in missing:
            print(f"  Missing: {p}")
        sys.exit("Run this script from src/exercises/ — input files not found")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")

    # ── 1. Columnar predicate pushdown ─────────────────────────────────────────
    print("=== 1. COLUMNAR PREDICATE PUSHDOWN ===")
    print("GeoParquet reads only the columns and row groups it needs.\n")

    print("  Writing places as GeoJSON for comparison (slow by design)...")
    places_gdf = gpd.read_parquet(PLACES_PARQUET)
    places_gdf.to_file(TMP_GEOJSON, driver='GeoJSON')
    try:
        t_parquet = best_of(
            con,
            f"SELECT COUNT(*) FROM read_parquet('{PLACES_PARQUET}') WHERE category = 'restaurant'",
        )
        t_geojson = best_of(
            con,
            f"SELECT COUNT(*) FROM ST_Read('{TMP_GEOJSON}') WHERE category = 'restaurant'",
        )
        n_restaurants = con.execute(
            f"SELECT COUNT(*) FROM read_parquet('{PLACES_PARQUET}') WHERE category = 'restaurant'"
        ).fetchone()[0]

        print(f"  Query: WHERE category = 'restaurant'  →  {n_restaurants:,} results")
        print(f"  GeoJSON (full text parse + scan): {t_geojson * 1000:.0f}ms")
        print(f"  GeoParquet (column pushdown):     {t_parquet * 1000:.1f}ms")
        print(f"  Speedup: {t_geojson / t_parquet:.0f}×")
    finally:
        if os.path.exists(TMP_GEOJSON):
            os.remove(TMP_GEOJSON)

    # ── 2. R-tree spatial index ────────────────────────────────────────────────
    print("\n=== 2. R-TREE SPATIAL INDEX ===")
    print("  Loading 42K places and 171K building polygons...")
    # Buildings geometry in the Parquet file is stored as WKB (BLOB) — decode to GEOMETRY.
    # Places geometry is also WKB-in-Parquet (from ST_AsWKB in Scout ETL) — geometry::GEOMETRY
    # decodes WKB → GEOMETRY. Both casts are required for R-tree index creation.
    #
    # NOTE: DuckDB 1.5 auto-decodes WKB from Parquet as GEOMETRY('OGC:CRS84') rather than
    # returning a plain BLOB, so ST_GeomFromWKB() fails (it only accepts BLOB). The
    # ::GEOMETRY cast strips the CRS annotation and works on both BLOB and typed GEOMETRY.
    con.execute(f"""
        CREATE TABLE buildings AS
        SELECT id, geometry::GEOMETRY AS geometry
        FROM read_parquet('{BUILDINGS_PARQUET}')
    """)
    con.execute(f"""
        CREATE TABLE places AS
        SELECT id, name, category, lat, lon, geometry::GEOMETRY AS geometry
        FROM read_parquet('{PLACES_PARQUET}')
    """)

    t_naive = best_of(
        con,
        "SELECT COUNT(*) FROM places p JOIN buildings b ON ST_Contains(b.geometry, p.geometry)",
        runs=3,
    )
    n_matches = con.execute(
        "SELECT COUNT(*) FROM places p JOIN buildings b ON ST_Contains(b.geometry, p.geometry)"
    ).fetchone()[0]
    print(f"  Naive join (42K × 171K): {n_matches:,} matches in {t_naive * 1000:.0f}ms")

    con.execute("CREATE INDEX bldg_rtree ON buildings USING RTREE (geometry)")
    print("  Created R-tree index on buildings.geometry")

    t_indexed = best_of(
        con,
        "SELECT COUNT(*) FROM places p JOIN buildings b ON ST_Contains(b.geometry, p.geometry)",
        runs=3,
    )
    print(f"  Indexed join:            {n_matches:,} matches in {t_indexed * 1000:.0f}ms")
    speedup_rtree = t_naive / t_indexed
    print(f"  Speedup: {speedup_rtree:.1f}×  (larger gains on disk-backed databases with repeated queries)")

    # ── 3. Two-stage filter ────────────────────────────────────────────────────
    print("\n=== 3. TWO-STAGE SPATIAL FILTER ===")
    print(f"  Center: SF City Hall ({CITY_HALL_LON}, {CITY_HALL_LAT})")
    print(f"  Radius: {RADIUS_DEG}° ≈ 2km\n")

    MARGIN = RADIUS_DEG * 1.1  # slightly larger bbox to avoid edge clipping

    total = con.execute(
        f"SELECT COUNT(*) FROM read_parquet('{PLACES_PARQUET}')"
    ).fetchone()[0]

    bbox_count = con.execute(f"""
        SELECT COUNT(*) FROM read_parquet('{PLACES_PARQUET}')
        WHERE lat  BETWEEN {CITY_HALL_LAT - MARGIN} AND {CITY_HALL_LAT + MARGIN}
          AND lon BETWEEN {CITY_HALL_LON - MARGIN} AND {CITY_HALL_LON + MARGIN}
    """).fetchone()[0]

    precise_count = con.execute(f"""
        SELECT COUNT(*) FROM (
            SELECT * FROM read_parquet('{PLACES_PARQUET}')
            WHERE lat  BETWEEN {CITY_HALL_LAT - MARGIN} AND {CITY_HALL_LAT + MARGIN}
              AND lon BETWEEN {CITY_HALL_LON - MARGIN} AND {CITY_HALL_LON + MARGIN}
        ) WHERE ST_DWithin(geometry, ST_Point({CITY_HALL_LON}, {CITY_HALL_LAT}), {RADIUS_DEG})
    """).fetchone()[0]

    t_naive_dwithin = best_of(con, f"""
        SELECT COUNT(*) FROM read_parquet('{PLACES_PARQUET}')
        WHERE ST_DWithin(geometry, ST_Point({CITY_HALL_LON}, {CITY_HALL_LAT}), {RADIUS_DEG})
    """)
    t_two_stage = best_of(con, f"""
        SELECT COUNT(*) FROM (
            SELECT * FROM read_parquet('{PLACES_PARQUET}')
            WHERE lat  BETWEEN {CITY_HALL_LAT - MARGIN} AND {CITY_HALL_LAT + MARGIN}
              AND lon BETWEEN {CITY_HALL_LON - MARGIN} AND {CITY_HALL_LON + MARGIN}
        ) WHERE ST_DWithin(geometry, ST_Point({CITY_HALL_LON}, {CITY_HALL_LAT}), {RADIUS_DEG})
    """)

    skipped = total - bbox_count
    print(f"  Stage 0 — all places:          {total:,}")
    print(f"  Stage 1 — bbox pre-filter:     {bbox_count:,}  ({skipped:,} rows skipped, {skipped/total*100:.1f}%)")
    print(f"  Stage 2 — ST_DWithin precise:  {precise_count:,}")
    print(f"  Naive ST_DWithin (no bbox):    {t_naive_dwithin*1000:.1f}ms")
    print(f"  Two-stage (bbox + DWithin):    {t_two_stage*1000:.1f}ms")
    print(f"  Note: for in-memory data the timing gap is small; at S3/disk scale")
    print(f"  the bbox filter cuts data transfer by {skipped/total*100:.0f}% before geometry runs.")

    # ── Visualization ─────────────────────────────────────────────────────────
    print("\n=== GENERATING VISUALIZATION ===")
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))

    # Left: columnar pushdown bar chart
    labels_push = ['GeoJSON\n(full parse)', 'GeoParquet\n(column pushdown)']
    times_push_ms = [t_geojson * 1000, t_parquet * 1000]
    colors_push = ['#e74c3c', '#2ecc71']
    bars0 = axes[0].bar(labels_push, times_push_ms, color=colors_push,
                        edgecolor='black', linewidth=0.8)
    for bar, val in zip(bars0, times_push_ms):
        label = f'{val:.0f}ms' if val >= 1 else f'{val * 1000:.0f}µs'
        axes[0].text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(times_push_ms) * 0.02,
            label, ha='center', va='bottom', fontweight='bold', fontsize=13,
        )
    axes[0].set_ylabel('Query time (ms, best of 5)', fontsize=12)
    axes[0].set_title(
        f'Predicate Pushdown\nWHERE category = \'restaurant\' ({n_restaurants:,} results)\n'
        f'{t_geojson / t_parquet:.0f}× faster with GeoParquet',
        fontweight='bold',
    )
    axes[0].set_ylim(0, max(times_push_ms) * 1.3)
    axes[0].grid(axis='y', alpha=0.3)

    # Right: two-stage filter funnel
    stage_labels = ['All places\n(full scan)', 'After bbox\npre-filter', 'After\nST_DWithin']
    stage_counts = [total, bbox_count, precise_count]
    stage_colors = ['#95a5a6', '#f39c12', '#27ae60']
    bars1 = axes[1].bar(stage_labels, stage_counts, color=stage_colors,
                        edgecolor='black', linewidth=0.8)
    for bar, val in zip(bars1, stage_counts):
        axes[1].text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + total * 0.005,
            f'{val:,}', ha='center', va='bottom', fontweight='bold', fontsize=12,
        )
    axes[1].set_ylabel('Rows evaluated', fontsize=12)
    axes[1].set_title(
        f'Two-Stage Spatial Filter (~2km from City Hall)\n'
        f'Bbox skips {skipped / total * 100:.0f}% of geometry evaluations',
        fontweight='bold',
    )
    axes[1].grid(axis='y', alpha=0.3)

    plt.tight_layout()
    out = f"{OUTPUT_DIR}/03_benchmark_results.png"
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {out}")

    # ── Summary table ──────────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("BENCHMARK SUMMARY")
    print("=" * 65)
    print(f"{'Benchmark':<35} {'Baseline':>10} {'Optimized':>10} {'Speedup':>8}")
    print("-" * 65)
    print(f"{'Columnar pushdown (category filter)':<35} "
          f"{t_geojson*1000:>8.0f}ms {t_parquet*1000:>8.1f}ms "
          f"{t_geojson/t_parquet:>6.0f}x")
    print(f"{'R-tree join (42K x 171K buildings)':<35} "
          f"{t_naive*1000:>8.0f}ms {t_indexed*1000:>8.0f}ms "
          f"{speedup_rtree:>6.1f}x")
    print(f"{'Two-stage filter (~2km from City Hall)':<35} "
          f"{t_naive_dwithin*1000:>8.1f}ms {t_two_stage*1000:>8.1f}ms "
          f"{t_naive_dwithin/t_two_stage:>6.1f}x")
    print("  (two-stage speedup is marginal in-memory; gains are larger at S3/disk scale)")
    print("-" * 65)
    print(f"Row reduction (two-stage): {total:,} → {bbox_count:,} → {precise_count:,} "
          f"({skipped/total*100:.0f}% skipped by bbox)")
    print("=" * 65)

    con.close()


if __name__ == "__main__":
    main()
