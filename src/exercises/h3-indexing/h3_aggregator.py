# Title: H3 Spatial Aggregator
# Description: Demonstrates fast spatial binning and hotspot analysis using Uber H3.

import h3
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point
import lonboard
from lonboard.colormap import apply_continuous_cmap
import palettable

def generate_synthetic_data(n=10000):
    """Generates synthetic pickup locations in San Francisco."""
    print(f"Generating {n} synthetic pickup points...")
    # SF Bounding Box approx
    lons = np.random.uniform(-122.51, -122.38, n)
    lats = np.random.uniform(37.70, 37.81, n)
    
    # Add some 'hotspots' (clusters)
    hotspot_lon, hotspot_lat = -122.4194, 37.7749 # Market St area
    cluster_lons = np.random.normal(hotspot_lon, 0.01, n // 2)
    cluster_lats = np.random.normal(hotspot_lat, 0.01, n // 2)
    
    final_lons = np.concatenate([lons[:n//2], cluster_lons])
    final_lats = np.concatenate([lats[:n//2], cluster_lats])
    
    return pd.DataFrame({'lon': final_lons, 'lat': final_lats})

def main():
    # 1. Setup Data
    df = generate_synthetic_data(10000)
    
    # 2. H3 Indexing (The "Quantization" step)
    # Mapping Lat/Lon to a 64-bit integer index (Resolution 9 ~ 0.1km area)
    RESOLUTION = 9
    print(f"Indexing points to H3 Resolution {RESOLUTION}...")
    df['h3_index'] = df.apply(lambda row: h3.latlng_to_cell(row['lat'], row['lon'], RESOLUTION), axis=1)
    
    # 3. Aggregation (The "Fast Join" step)
    # We no longer need geometry! We just group by the H3 string/integer.
    print("Aggregating hotspots...")
    h3_counts = df.groupby('h3_index').size().reset_index(name='pickup_count')
    
    # 4. Convert H3 to Geometry for Visualization
    # We only create geometries at the very end for the human/UI.
    print("Generating hexagon geometries for visualization...")
    h3_counts['geometry'] = h3_counts['h3_index'].apply(
        lambda x: Point(h3.cell_to_latlng(x)[::-1])
    )
    
    # For Lonboard we want the actual hexagon boundaries
    hex_geoms = h3_counts['h3_index'].apply(
        lambda x: gpd.GeoSeries([Point(p[::-1]) for p in h3.cell_to_boundary(x)]).union_all().convex_hull
    )
    
    gdf = gpd.GeoDataFrame(h3_counts, geometry=hex_geoms, crs="EPSG:4326")
    
    print(f"Aggregated {len(df)} points into {len(gdf)} unique hexagons.")
    
    # 5. Visualization with Lonboard
    print("Creating Lonboard visualization...")
    layer = lonboard.PolygonLayer.from_geopandas(gdf)
    
    # Color by pickup count
    normalized_counts = (gdf['pickup_count'] - gdf['pickup_count'].min()) / (gdf['pickup_count'].max() - gdf['pickup_count'].min())
    layer.fill_color = apply_continuous_cmap(normalized_counts, palettable.colorbrewer.sequential.YlOrRd_9)
    
    # Create Map and Save to HTML
    output_html = "h3_hotspots.html"
    m = lonboard.Map(layers=[layer])
    m.to_html(output_html)
    
    print(f"\n✅ SUCCESS: H3 analysis complete.")
    print(f"Exercise Results: {output_html}")

if __name__ == "__main__":
    main()
