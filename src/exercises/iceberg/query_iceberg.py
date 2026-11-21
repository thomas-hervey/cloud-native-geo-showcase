# Title: Query Iceberg Table
# Description: Demonstrate Time Travel and DuckDB integration with Iceberg
from pyiceberg.catalog import load_catalog
import duckdb
import pandas as pd
import geopandas as gpd
from shapely import wkb

def main():
    print("Loading local Iceberg catalog...")
    catalog = load_catalog("local", **{
        "type": "sql",
        "uri": "sqlite:///iceberg_catalog.db",
        "warehouse": "./warehouse",
    })

    # 1. Load Table
    table = catalog.load_table("geo_tutorial.points")
    
    # 2. Show History (Snapshots)
    print("\n--- TABLE HISTORY ---")
    for snapshot in table.history():
        print(f"Snapshot ID: {snapshot.snapshot_id} | Created at: {snapshot.timestamp_ms}")

    # 3. Query Current Data (Scan to Pandas)
    print("\n--- QUERYING CURRENT SNAPSHOT ---")
    arrow_table = table.scan().to_arrow()
    df = arrow_table.to_pandas()
    
    # Convert WKB back to Geometry for GeoPandas
    df['geometry'] = df['geometry'].apply(wkb.loads)
    gdf = gpd.GeoDataFrame(df, crs="EPSG:4326")
    
    print(f"Total points in current version: {len(gdf)}")

    # 4. Time Travel (Query Snapshot 1)
    print("\n--- TIME TRAVEL ---")
    history = list(table.history())
    if len(history) > 1:
        first_snapshot_id = history[0].snapshot_id
        print(f"Scanning Snapshot ID: {first_snapshot_id} (Batch 1 only)...")
        
        old_df = table.scan(snapshot_id=first_snapshot_id).to_pandas()
        print(f"Points in Snapshot 1: {len(old_df)}")
    
    # 5. DuckDB Integration (SQL Scan)
    print("\n--- DUCKDB SQL ON ICEBERG ---")
    con = table.scan().to_duckdb(table_name="iceberg_points")
    
    # 5a. Simple Attribute Filter
    result = con.execute("""
        SELECT count(*) 
        FROM iceberg_points 
        WHERE value > 0
    """).fetchone()
    print(f"Points with positive value (via DuckDB): {result[0]}")

    # 5b. Spatial Filter
    # DuckDB's spatial extension allows us to treat the Iceberg scan like a PostGIS table.
    print("\n--- SPATIAL SQL FILTER ---")
    con.execute("INSTALL spatial; LOAD spatial;")
    
    # Find points within a specific bounding box (SF District)
    spatial_result = con.execute("""
        SELECT count(*)
        FROM iceberg_points
        WHERE ST_Intersects(
            ST_GeomFromWKB(geometry),
            ST_MakeEnvelope(-122.45, 37.75, -122.40, 37.78)
        )
    """).fetchone()
    
    print(f"Points within SF Bounding Box: {spatial_result[0]}")

if __name__ == "__main__":
    main()