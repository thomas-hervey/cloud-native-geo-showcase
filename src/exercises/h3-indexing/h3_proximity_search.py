# Title: H3 Proximity & Compaction
# Description: Demonstrates complex spatial operations (Grid Distance & Compaction) simplified by H3.

import h3
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point, mapping
import lonboard
from lonboard.colormap import apply_continuous_cmap
import palettable

def main():
    # 1. Setup: A "Store" and some "Users"
    store_lat, store_lon = 37.7749, -122.4194  # Market St, SF
    RES = 9
    store_cell = h3.latlng_to_cell(store_lat, store_lon, RES)
    
    print(f"Store Location: {store_lat}, {store_lon} (H3: {store_cell})")
    
    # Generate random users within SF
    n_users = 2000
    user_lons = np.random.uniform(-122.50, -122.38, n_users)
    user_lats = np.random.uniform(37.72, 37.81, n_users)
    users_df = pd.DataFrame({'lat': user_lats, 'lon': user_lons})
    users_df['h3_index'] = users_df.apply(lambda r: h3.latlng_to_cell(r['lat'], r['lon'], RES), axis=1)
    
    # 2. Grid Distance (K-Ring / Grid Disk)
    # Find all hexagons within k steps (approx 1.5km for Res 9)
    K_STEPS = 5
    print(f"Calculating Catchment Zone (k={K_STEPS})...")
    catchment_cells = h3.grid_disk(store_cell, K_STEPS)
    
    # 3. Proximity Search (The Power of Sets)
    # Traditionally, you'd do: for user in users: if user.dist(store) < R
    # With H3, we just check if the user's ID is in our set of catchment IDs.
    print("Performing set-based proximity search...")
    catchment_set = set(catchment_cells)
    users_df['in_catchment'] = users_df['h3_index'].isin(catchment_set)
    
    near_users_count = users_df['in_catchment'].sum()
    print(f"Found {near_users_count} users within the catchment zone.")
    
    # 4. Hierarchical Compaction
    # Catchments can be huge. Instead of sending 300 hexagons to the frontend,
    # we can 'compact' them into larger parents where possible.
    print(f"Original cells: {len(catchment_cells)}")
    compacted_cells = h3.compact_cells(catchment_cells)
    print(f"Compacted cells: {len(compacted_cells)} (Compression: {1 - len(compacted_cells)/len(catchment_cells):.1%})")
    
    # 5. Visualization Preparation
    # Prepare catchment for viz
    def cell_to_geom(c):
        return gpd.GeoSeries([Point(p[::-1]) for p in h3.cell_to_boundary(c)]).union_all().convex_hull

    catchment_gdf = gpd.GeoDataFrame(
        {'h3_index': list(compacted_cells)},
        geometry=[cell_to_geom(c) for c in compacted_cells],
        crs="EPSG:4326"
    )
    
    # Prepare users for viz
    users_gdf = gpd.GeoDataFrame(
        users_df,
        geometry=[Point(lon, lat) for lon, lat in zip(users_df.lon, users_df.lat)],
        crs="EPSG:4326"
    )
    
    # 6. Create Lonboard Map
    print("Creating visualization...")
    catchment_layer = lonboard.PolygonLayer.from_geopandas(catchment_gdf)
    catchment_layer.fill_color = [0, 0, 255, 100]  # Translucent Blue
    
    user_layer = lonboard.ScatterplotLayer.from_geopandas(users_gdf)
    # Color: Red if in catchment, Gray if outside
    user_layer.get_fill_color = np.array([
        [255, 0, 0, 200] if in_z else [128, 128, 128, 100] 
        for in_z in users_df.in_catchment
    ], dtype=np.uint8)
    user_layer.get_radius = 20
    
    m = lonboard.Map(layers=[catchment_layer, user_layer])
    output_html = "h3_proximity.html"
    m.to_html(output_html)
    
    print(f"\n✅ SUCCESS: Proximity analysis complete.")
    print(f"Catchment Visualization: {output_html}")
    print("\nTakeaways:")
    print("- Grid Distance: No trigonometry required.")
    print("- Set Lookup: O(1) complexity per user.")
    print("- Compaction: Efficient storage for high-res zones.")

if __name__ == "__main__":
    main()
