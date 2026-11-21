import duckdb

def main():
    print("--- 1. INITIALIZING DUCKDB SPATIAL ---")
    con = duckdb.connect()
    
    # Enable HTTPFS and SPATIAL
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute("INSTALL spatial; LOAD spatial;")
    
    # Configure S3 for anonymous access
    # Overture data is public, so no AWS credentials are required for simple reads
    con.execute("SET s3_region='us-west-2';")
    con.execute("SET s3_access_key_id='';")
    con.execute("SET s3_secret_access_key='';")

    release = "2026-01-21.0"
    places_url = f"s3://overturemaps-us-west-2/release/{release}/theme=places/type=place/*"
    
    print("\n--- 2. ADVANCED SPATIAL QUERY ---")
    print("Goal: Find places strictly within a 1km radius of the Golden Gate Bridge...")

    # We define a "search area" as a WKT polygon (a rough circle/diamond)
    # Center approx: -122.478, 37.819
    # We use ST_Intersects to show true Spatial SQL power
    query = f"""
    SELECT 
        names.primary as name,
        basic_category as category,
        ST_AsWKB(geometry) as geom
    FROM read_parquet('{places_url}')
    WHERE 
        bbox.xmin > -122.50 AND bbox.xmax < -122.45 AND
        bbox.ymin > 37.80 AND bbox.ymax < 37.85 AND
        ST_Intersects(
            geometry,
            ST_Buffer(ST_Point(-122.478, 37.819), 0.01)
        )
    LIMIT 20;
    """
    
    import time
    start_time = time.time()
    df = con.execute(query).df()
    
    # Convert to GeoDataFrame for visualization
    import geopandas as gpd
    gdf = gpd.GeoDataFrame(df, geometry=gpd.GeoSeries.from_wkb(df['geom'].apply(bytes)), crs="EPSG:4326")
    
    end_time = time.time()
    
    print(f"Retrieved {len(gdf)} places via spatial intersection in {end_time - start_time:.2f}s")
    print("\nResults:")
    print(gdf[['name', 'category']].head())

    print("\n--- 3. VISUALIZING RESULTS ---")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FormatStrFormatter
    
    fig, ax = plt.subplots(figsize=(10, 10))
    gdf.plot(ax=ax, column='category', legend=True, 
             markersize=100, cmap='viridis', alpha=0.8,
             legend_kwds={'bbox_to_anchor': (1, 1)})
    
    ax.set_aspect('equal')
    ax.xaxis.set_major_formatter(FormatStrFormatter('%.3f'))
    ax.set_title("Overture Places near Golden Gate Bridge")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.grid(True, alpha=0.2)
    
    ctx_url = "overture_preview.png"
    plt.savefig(ctx_url, bbox_inches='tight', dpi=150)
    print(f"Quick preview saved to: {ctx_url}")

    print("\n--- 4. DATA COMMONS POWER ---")
    print("You just performed a complex spatial intersection against a multi-TB")
    print("global dataset without a GIS server. This is 'Data as an API'.")
    
    con.close()

if __name__ == "__main__":
    main()
