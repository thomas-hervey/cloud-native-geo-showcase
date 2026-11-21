"""
Exercise 1: Spatial Predicates & Measurements
=============================================
Motivating question: Which SF neighborhoods have the most restaurants,
and which food/drink places are walkable from Dolores Park?

Run from src/exercises/:
    uv run python duckdb-spatial/01_predicates_and_measurements.py

Output:
    duckdb-spatial/output/01_sf_neighborhood_analysis.png
"""
import os
import sys
import duckdb
import geopandas as gpd
import matplotlib.pyplot as plt

NEIGHBORHOODS = "spatial-eval/data/Analysis_Neighborhoods_20260309.geojson"
PLACES = "scout-etl/output/sf_places.parquet"
OUTPUT_DIR = "duckdb-spatial/output"

# At SF's latitude (~37.7°N): 1° ≈ 111,000m
# 500m ≈ 0.0045°  |  1km ≈ 0.009°
# ST_Transform is not used (PROJ data not bundled in DuckDB extension).
# Degree-based distances are a standard approximation for local-area analysis.
DOLORES_LON, DOLORES_LAT = -122.4268, 37.7596
WALKABLE_DEG = 500 / 111_000  # ~0.0045°


def main():
    missing = [p for p in [NEIGHBORHOODS, PLACES] if not os.path.exists(p)]
    if missing:
        for p in missing:
            print(f"  Missing: {p}")
        sys.exit("Run this script from src/exercises/ — input files not found")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")

    # ── Load data ─────────────────────────────────────────────────────────────
    print("=== LOADING DATA ===")
    # ST_Read returns GEOMETRY with CRS info; read_parquet returns WKB (BLOB) from Scout ETL.
    # Both are cast to base GEOMETRY type, required for spatial joins.
    con.execute(f"""
        CREATE TABLE neighborhoods AS
        SELECT nhood, geom::GEOMETRY AS geometry
        FROM ST_Read('{NEIGHBORHOODS}')
    """)
    con.execute(f"""
        CREATE TABLE places AS
        SELECT id, name, category, lat, lon, geometry::GEOMETRY AS geometry
        FROM read_parquet('{PLACES}')
    """)
    n_nbhoods = con.execute("SELECT COUNT(*) FROM neighborhoods").fetchone()[0]
    n_places = con.execute("SELECT COUNT(*) FROM places").fetchone()[0]
    print(f"Loaded {n_nbhoods} neighborhoods, {n_places:,} places\n")

    # ── Spatial predicates ────────────────────────────────────────────────────
    print("=== SPATIAL PREDICATES ===")

    # ST_Intersects: places in the Mission District
    mission_sample = con.execute("""
        SELECT p.name, p.category
        FROM places p
        JOIN neighborhoods n ON ST_Intersects(p.geometry, n.geometry)
        WHERE n.nhood = 'Mission'
        ORDER BY p.category, p.name
        LIMIT 10
    """).df()
    print("Sample places in the Mission (ST_Intersects):")
    print(mission_sample.to_string(index=False))

    # ST_Contains vs ST_Within: same result, subject/object swapped
    n_contains = con.execute("""
        SELECT COUNT(*) FROM neighborhoods n
        JOIN places p ON ST_Contains(n.geometry, p.geometry)
        WHERE n.nhood = 'Mission'
    """).fetchone()[0]
    n_within = con.execute("""
        SELECT COUNT(*) FROM places p
        JOIN neighborhoods n ON ST_Within(p.geometry, n.geometry)
        WHERE n.nhood = 'Mission'
    """).fetchone()[0]
    print(f"\nST_Contains(neighborhood, place): {n_contains} places in Mission")
    print(f"ST_Within(place, neighborhood):   {n_within} places in Mission (same result, flipped subject)")

    # ── Measurements ──────────────────────────────────────────────────────────
    print("\n=== SPATIAL MEASUREMENTS ===")

    # ST_Area in sq-degrees (relative comparison; absolute units require ST_Transform + PROJ)
    areas = con.execute("""
        SELECT nhood,
               ROUND(ST_Area(geometry) * 1e4, 4) AS area_x1e4_sqdeg
        FROM neighborhoods
        ORDER BY area_x1e4_sqdeg DESC
        LIMIT 10
    """).df()
    print("Top 10 neighborhoods by area (relative, larger = bigger):")
    print(areas.to_string(index=False))

    # ST_Distance: closest food/drink to Dolores Park
    # Multiply degrees × 111,000 for approximate meters (±1% at SF latitude)
    closest = con.execute(f"""
        SELECT name, category,
               ROUND(ST_Distance(geometry, ST_Point({DOLORES_LON}, {DOLORES_LAT})) * 111_000, 0)
                   AS approx_dist_m
        FROM places
        WHERE category IN ('restaurant', 'bar', 'cafe', 'bakery', 'beverage_shop')
        ORDER BY ST_Distance(geometry, ST_Point({DOLORES_LON}, {DOLORES_LAT}))
        LIMIT 10
    """).df()
    print("\nClosest food/drink to Dolores Park (ST_Distance, approx meters):")
    print(closest.to_string(index=False))

    # ST_Centroid: neighborhood centroids
    centroids = con.execute("""
        SELECT nhood, ST_AsText(ST_Centroid(geometry)) AS centroid
        FROM neighborhoods
        ORDER BY nhood
        LIMIT 5
    """).df()
    print("\nNeighborhood centroids (ST_Centroid):")
    print(centroids.to_string(index=False))

    # ── ST_DWithin ────────────────────────────────────────────────────────────
    print(f"\n=== ST_DWithin: 500m from Dolores Park ({WALKABLE_DEG:.4f}°) ===")
    near_dolores = con.execute(f"""
        SELECT name, category,
               ROUND(ST_Distance(geometry, ST_Point({DOLORES_LON}, {DOLORES_LAT})) * 111_000, 0)
                   AS approx_dist_m
        FROM places
        WHERE category IN ('restaurant', 'bar', 'cafe', 'bakery', 'beverage_shop')
          AND ST_DWithin(geometry, ST_Point({DOLORES_LON}, {DOLORES_LAT}), {WALKABLE_DEG})
        ORDER BY approx_dist_m
    """).df()
    print(f"{len(near_dolores)} food/drink places within 500m of Dolores Park:")
    print(near_dolores.to_string(index=False))

    # ── Aggregate: restaurant density per neighborhood ─────────────────────────
    print("\n=== TOP NEIGHBORHOODS BY RESTAURANT COUNT ===")
    density = con.execute("""
        SELECT n.nhood,
               COUNT(*) AS restaurant_count
        FROM neighborhoods n
        JOIN places p ON ST_Contains(n.geometry, p.geometry)
        WHERE p.category = 'restaurant'
        GROUP BY n.nhood, n.geometry
        ORDER BY restaurant_count DESC
        LIMIT 10
    """).df()
    print(density.to_string(index=False))

    # ── Visualization ─────────────────────────────────────────────────────────
    print("\n=== GENERATING VISUALIZATION ===")

    all_nbhood_counts = con.execute("""
        SELECT n.nhood,
               COUNT(p.id) AS restaurant_count,
               ST_AsWKB(n.geometry) AS geom_wkb
        FROM neighborhoods n
        LEFT JOIN places p
            ON ST_Contains(n.geometry, p.geometry) AND p.category = 'restaurant'
        GROUP BY n.nhood, n.geometry
    """).df()

    dolores_pts = con.execute(f"""
        SELECT name, category,
               ST_X(geometry) AS lon,
               ST_Y(geometry) AS lat
        FROM places
        WHERE category IN ('restaurant', 'bar', 'cafe', 'bakery', 'beverage_shop')
          AND ST_DWithin(geometry, ST_Point({DOLORES_LON}, {DOLORES_LAT}), {WALKABLE_DEG})
    """).df()

    nbhoods_gdf = gpd.GeoDataFrame(
        all_nbhood_counts,
        geometry=gpd.GeoSeries.from_wkb(all_nbhood_counts['geom_wkb'].apply(bytes)),
        crs="EPSG:4326",
    )

    fig, axes = plt.subplots(1, 2, figsize=(16, 8))

    # Left panel: choropleth by restaurant count
    nbhoods_gdf.plot(
        ax=axes[0], column='restaurant_count', cmap='YlOrRd',
        legend=True, legend_kwds={'label': 'Restaurant count', 'shrink': 0.7},
        edgecolor='white', linewidth=0.5,
    )
    axes[0].set_title(
        'SF Neighborhoods — Restaurant Count\n(DuckDB ST_Contains spatial join)',
        fontweight='bold', fontsize=11,
    )
    axes[0].set_xlabel('Longitude')
    axes[0].set_ylabel('Latitude')
    axes[0].grid(True, alpha=0.2)

    # Right panel: Dolores Park 500m walkable scatter
    nbhoods_gdf.plot(ax=axes[1], color='#f5f5f5', edgecolor='#cccccc', linewidth=0.4)
    cat_colors = {
        'restaurant': '#e74c3c', 'bar': '#8e44ad',
        'cafe': '#2980b9', 'bakery': '#e67e22', 'beverage_shop': '#27ae60',
    }
    for cat, clr in cat_colors.items():
        sub = dolores_pts[dolores_pts['category'] == cat]
        if len(sub):
            axes[1].scatter(sub['lon'], sub['lat'], c=clr, s=70,
                            label=cat, alpha=0.85, zorder=5)
    axes[1].scatter(
        [DOLORES_LON], [DOLORES_LAT],
        marker='*', s=400, c='gold', edgecolors='black', lw=1, zorder=10,
        label='Dolores Park',
    )
    circle = plt.Circle(
        (DOLORES_LON, DOLORES_LAT), WALKABLE_DEG,
        fill=False, color='black', ls='--', lw=1.5, zorder=8,
    )
    axes[1].add_patch(circle)
    axes[1].set_xlim(-122.47, -122.39)
    axes[1].set_ylim(37.74, 37.78)
    axes[1].set_title(
        f'Food/Drink within 500m of Dolores Park\n(ST_DWithin, n={len(dolores_pts)})',
        fontweight='bold', fontsize=11,
    )
    axes[1].legend(loc='lower right', fontsize=8)
    axes[1].set_xlabel('Longitude')
    axes[1].set_ylabel('Latitude')
    axes[1].grid(True, alpha=0.2)

    plt.tight_layout()
    out = f"{OUTPUT_DIR}/01_sf_neighborhood_analysis.png"
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {out}")

    con.close()


if __name__ == "__main__":
    main()
