import duckdb
import geopandas as gpd
import json
import time

def main():
    print("--- 1. LOADING DATA (TRADITIONAL WAY) ---")
    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute("SET s3_region='us-west-2';")
    con.execute("SET s3_access_key_id='';")
    con.execute("SET s3_secret_access_key='';")

    release = "2026-01-21.0"
    places_url = f"s3://overturemaps-us-west-2/release/{release}/theme=places/type=place/*"

    print("Querying Overture for SF POIs...")
    query = """
    SELECT 
        names.primary as name,
        basic_category as category,
        ST_AsWKB(geometry) as geom
    FROM read_parquet('""" + places_url + """')
    WHERE 
        bbox.xmin > -122.51 AND bbox.xmax < -122.35 AND
        bbox.ymin > 37.70 AND bbox.ymax < 37.83;
    """
    
    start_data = time.time()
    df = con.execute(query).df()
    gdf = gpd.GeoDataFrame(df, geometry=gpd.GeoSeries.from_wkb(df['geom'].apply(bytes)), crs="EPSG:4326")
    gdf = gdf.drop(columns=['geom'])
    end_data = time.time()
    
    print(f"Retrieved {len(gdf)} features in {end_data - start_data:.2f}s")

    print("\n--- 2. THE TRADITIONAL OVERHEAD ---")
    print("In traditional apps, we often convert to GeoJSON for the browser.")
    
    start_geojson = time.time()
    # Simulating standard GeoJSON conversion
    geojson_data = gdf.head(5000).to_json() # Only 5000 to keep it manageable
    end_geojson = time.time()
    
    geojson_size_mb = len(geojson_data.encode('utf-8')) / (1024 * 1024)
    
    print(f"Time to serialize JUST 5,000 features to GeoJSON: {end_geojson - start_geojson:.2f}s")
    print(f"Size of 5,000 features in GeoJSON: {geojson_size_mb:.2f} MB")
    
    total_est_size = (geojson_size_mb / 5000) * len(gdf)
    print(f"ESTIMATED size for all {len(gdf)} features: {total_est_size:.2f} MB")

    print("\n--- 3. THE RASTER TILE 'SOLUTION' ---")
    print("To avoid the GeoJSON bloat, traditional apps use Raster Tiling.")
    print("Fetching a single 256x256 image tile for this area...")

    import requests
    # OSM Tile for the Golden Gate area (Zoom 15)
    tile_url = "https://tile.openstreetmap.org/15/5241/12663.png"
    headers = {'User-Agent': 'CloudNativeTutorial/1.0'}
    
    try:
        start_tile = time.time()
        response = requests.get(tile_url, headers=headers)
        end_tile = time.time()
        
        tile_size_kb = len(response.content) / 1024
        print(f"Retrieved 1 PNG tile in {end_tile - start_tile:.2f}s")
        print(f"Tile Size: {tile_size_kb:.2f} KB (Tiny compared to 30MB JSON!)")
        
        with open("traditional_tile.png", "wb") as f:
            f.write(response.content)
        print("Tile saved to: traditional_tile.png")
    except Exception as e:
        print(f"Failed to fetch tile: {e}")

    print("\n--- 4. THE TRADEOFF ANALYSIS ---")
    print("1. Speed: Tiles are fast because they are just images.")
    print("2. Interactivity: Once it's a PNG, you CANNOT click a building to see its name.")
    print("   You would have to make a separate 'GetFeatureInfo' API call to the server.")
    print("3. Stale Data: Tiles are often pre-rendered. If the Overture data updates,")
    print("   you have to wait for the server to re-draw every single tile in the world.")

if __name__ == "__main__":
    main()
