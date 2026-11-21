# Title: GeoParquet Benchmark
# Description: Compare file size and I/O speed of GeoJSON vs GeoParquet
import geopandas as gpd
import pandas as pd
import numpy as np
import time
import matplotlib.pyplot as plt
import os

def main():
    # 1. Generate Dummy Data (100,000 points)
    n_points = 100_000
    print(f"Generating {n_points} random points...")
    
    # Random coordinates
    longitudes = np.random.uniform(-180, 180, n_points)
    latitudes = np.random.uniform(-90, 90, n_points)
    
    # Create GeoDataFrame
    df = pd.DataFrame({
        'id': range(n_points),
        'value': np.random.randn(n_points),
        'category': np.random.choice(['A', 'B', 'C'], n_points)
    })
    gdf = gpd.GeoDataFrame(
        df, 
        geometry=gpd.points_from_xy(longitudes, latitudes),
        crs="EPSG:4326"
    )
    
    # 2. Write GeoJSON
    print("Writing GeoJSON (this might be slow)...")
    start = time.time()
    gdf.to_file("data.geojson", driver="GeoJSON")
    geojson_time = time.time() - start
    
    # 3. Write GeoParquet
    print("Writing GeoParquet...")
    start = time.time()
    gdf.to_parquet("data.parquet")
    parquet_time = time.time() - start
    
    # 4. Compare Size
    geojson_size = os.path.getsize("data.geojson") / (1024 * 1024) # MB
    parquet_size = os.path.getsize("data.parquet") / (1024 * 1024) # MB
    
    print("\n--- RESULTS ---")
    print(f"GeoJSON Write Time:   {geojson_time:.2f}s")
    print(f"GeoParquet Write Time: {parquet_time:.2f}s")
    print(f"Speedup: {geojson_time/parquet_time:.1f}x faster")
    
    print(f"\nGeoJSON Size:   {geojson_size:.2f} MB")
    print(f"GeoParquet Size: {parquet_size:.2f} MB")
    print(f"Compression: {(1 - parquet_size/geojson_size)*100:.1f}% smaller")
    
    # 5. Read Benchmark (Columnar Access)
    print("\n--- READ BENCHMARK (Reading ONLY the 'category' column) ---")
    
    # GeoJSON: Must read everything
    start = time.time()
    # Note: fiona/gpd doesn't easily support column selection for GeoJSON at read time without parsing
    _ = gpd.read_file("data.geojson")
    geojson_read_time = time.time() - start
    print(f"GeoJSON Read Time (Full): {geojson_read_time:.2f}s")
    
    # GeoParquet: Read attributes ONLY (using pandas for raw speed)
    start = time.time()
    # This is a key "Cloud Native" benefit - we can treat geospatial data
    # as a standard columnar table when we don't need the geometry!
    _ = pd.read_parquet("data.parquet", columns=["category"])
    parquet_attr_time = time.time() - start
    print(f"GeoParquet Read Time (Attributes only via Pandas): {parquet_attr_time:.2f}s")
    
    # GeoParquet: Read spatial + attributes (using geopandas)
    start = time.time()
    # Note: geopandas requires the 'geometry' column to create a GeoDataFrame
    _ = gpd.read_parquet("data.parquet", columns=["category", "geometry"])
    parquet_geo_time = time.time() - start
    print(f"GeoParquet Read Time (Spatial + Attr via GeoPandas): {parquet_geo_time:.2f}s")

    # 6. Visualization
    print("\n--- VISUALIZATION ---")
    print("Plotting a sample of the data...")
    # Plotting 100k points is slow, let's take a sample
    sample_gdf = gdf.sample(1000)
    plt.figure(figsize=(10, 6))
    sample_gdf.plot(column='category', legend=True, alpha=0.5, ax=plt.gca())
    plt.title("GeoParquet Sample Plot (1000 points)")
    plt.savefig("vector_plot.png")
    print("Saved 'vector_plot.png'")

    # 7. Spatial Query
    print("\n--- SPATIAL QUERY ---")
    # Define a small bounding box
    xmin, ymin, xmax, ymax = 0, 0, 10, 10
    print(f"Querying points within bounds [{xmin}, {ymin}, {xmax}, {ymax}]...")
    
    start = time.time()
    # Standard GeoParquet approach: Read and then filter spatially
    # Even this is fast because GeoParquet is optimized for these bulk operations
    full_gdf = gpd.read_parquet("data.parquet")
    spatial_subset = full_gdf.cx[xmin:xmax, ymin:ymax]
    spatial_time = time.time() - start
    
    print(f"Found {len(spatial_subset)} points in {spatial_time:.4f}s")
    print("\nSuccess! Even with 100k points, spatial sub-setting is nearly instant.")

if __name__ == "__main__":
    main()