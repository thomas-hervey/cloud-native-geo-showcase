import requests
import time
import mapbox_vector_tile
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import shape

def main():
    print("--- 1. THE VECTOR TILE MIDDLE GROUND ---")
    print("Vector Tiles (MVT) send compressed geometry (PBF) instead of pixels.")
    print("This allows the browser to draw the data, enabling hover/click.")
    
    # Using MapLibre demo tiles which are reliable and don't require keys
    # Zoom 0, X=0, Y=0 (Global view)
    tile_url = "https://demotiles.maplibre.org/tiles/0/0/0.pbf"
    headers = {'User-Agent': 'CloudNativeTutorial/1.0'}
    
    print(f"\nFetching Vector Tile: {tile_url}")
    
    try:
        start_time = time.time()
        response = requests.get(tile_url, headers=headers)
        end_time = time.time()
        
        if response.status_code != 200:
            print(f"Failed to fetch tile (Status: {response.status_code})")
            return

        tile_data = response.content
        size_kb = len(tile_data) / 1024
        
        print(f"Retrieved 1 MVT tile in {end_time - start_time:.2f}s")
        print(f"Tile Size: {size_kb:.2f} KB")

        print("\n--- 2. DECODING & VISUALIZING ---")
        decoded_tile = mapbox_vector_tile.decode(tile_data)
        
        print(f"Layers found in this tile: {', '.join(decoded_tile.keys())}")
        
        # We will collect all features into a GeoDataFrame for visualization
        all_features = []
        for layer_name, layer in decoded_tile.items():
            print(f"Processing layer '{layer_name}' ({len(layer['features'])} features)...")
            for feat in layer['features']:
                # The 'geometry' in MVT is in tile-local coordinates (0-4096)
                # For this demo, we'll just plot the raw shapes to show they exist
                geom = shape(feat['geometry'])
                props = feat['properties']
                props['layer'] = layer_name
                all_features.append({'geometry': geom, **props})
        
        if all_features:
            gdf = gpd.GeoDataFrame(all_features)
            
            # Simple plot
            fig, ax = plt.subplots(figsize=(10, 10))
            gdf.plot(ax=ax, column='layer', legend=True, cmap='tab10')
            ax.set_title("Vector Tile Data (Decoded from PBF)")
            plt.savefig("vector_tile_preview.png")
            print("\nVisualization saved to: vector_tile_preview.png")
            print(f"Total features visualized: {len(gdf)}")
        else:
            print("\nNo features found to visualize.")

    except Exception as e:
        print(f"Error during Vector Tile demo: {e}")

    print("\n--- 3. THE ARCHITECTURAL TRADEOFF ---")
    print("1. Interactivity: YES! The browser has the coordinates and names.")
    print("2. Clipping: MVTs are 'clipped' to tile boundaries.")
    print("3. Complexity: Notice the effort to decode PBF and handle tile-local coordinates.")
    print("\nCloud-Native (GeoArrow) sends the REAL world coordinates directly to the GPU.")

if __name__ == "__main__":
    main()
