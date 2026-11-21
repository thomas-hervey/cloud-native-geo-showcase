# Title: Create Iceberg Table
# Description: Initialize a local Iceberg catalog and create a table with geospatial data
import pandas as pd
import geopandas as gpd
import numpy as np
import pyarrow as pa
from pyiceberg.catalog import load_catalog
import os
import shutil

def main():
    # 1. Cleanup previous runs
    if os.path.exists("warehouse"):
        shutil.rmtree("warehouse")
    if os.path.exists("iceberg_catalog.db"):
        os.remove("iceberg_catalog.db")

    print("Initializing local Iceberg catalog...")
    # We use a SQL-based catalog (SQLite) for zero-infrastructure local development
    catalog = load_catalog("local", **{
        "type": "sql",
        "uri": "sqlite:///iceberg_catalog.db",
        "warehouse": "./warehouse",
    })

    # 2. Prepare Sample Data (Batch 1)
    print("Generating sample points (Batch 1)...")
    n_points = 1000
    df1 = pd.DataFrame({
        'id': range(n_points),
        'name': [f"Point_{i}" for i in range(n_points)],
        'value': np.random.randn(n_points)
    })
    # For Iceberg, we convert geometry to WKB (Well-Known Binary) 
    # as it's the standard for GeoParquet columns
    longitudes = np.random.uniform(-122.5, -122.3, n_points)
    latitudes = np.random.uniform(37.7, 37.8, n_points)
    gdf1 = gpd.GeoDataFrame(df1, geometry=gpd.points_from_xy(longitudes, latitudes), crs="EPSG:4326")
    
    # Convert to Arrow Table (Iceberg uses Arrow for ingestion)
    df1['geometry'] = gdf1.geometry.to_wkb()
    table1 = pa.Table.from_pandas(df1)

    # 3. Create Table
    print("Creating Iceberg table 'geo_tutorial.points'...")
    catalog.create_namespace("geo_tutorial")
    
    iceberg_table = catalog.create_table(
        "geo_tutorial.points",
        schema=table1.schema
    )

    # 4. Append Data (Snapshot 1)
    print("Appending Batch 1 (Snapshot 1)...")
    iceberg_table.append(table1)

    # 5. Append More Data (Snapshot 2)
    print("Generating and appending Batch 2 (Snapshot 2)...")
    df2 = pd.DataFrame({
        'id': range(n_points, n_points * 2),
        'name': [f"Point_{i}" for i in range(n_points, n_points * 2)],
        'value': np.random.randn(n_points)
    })
    longitudes2 = np.random.uniform(-122.5, -122.3, n_points)
    latitudes2 = np.random.uniform(37.7, 37.8, n_points)
    gdf2 = gpd.GeoDataFrame(df2, geometry=gpd.points_from_xy(longitudes2, latitudes2), crs="EPSG:4326")
    df2['geometry'] = gdf2.geometry.to_wkb()
    table2 = pa.Table.from_pandas(df2)
    
    iceberg_table.append(table2)

    print("\nSuccess! Iceberg table created and populated.")
    print(f"Warehouse location: {os.path.abspath('warehouse')}")



if __name__ == "__main__":
    main()