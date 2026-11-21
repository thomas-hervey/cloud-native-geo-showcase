# Title: Cloud-Native Imagery Pipeline
# Description: STAC -> stackstac -> Features -> K-Means -> Sieve -> GeoParquet
import pystac_client
import planetary_computer
import stackstac
import numpy as np
import xarray as xr
from sklearn.cluster import KMeans
import rasterio.features
from shapely.geometry import shape
import geopandas as gpd
import matplotlib.pyplot as plt
import os
import duckdb

def main():
    # 1. Search and Load Data (Remote Chipping)
    print("Searching for Sentinel-2 data...")
    catalog = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace,
    )

    # Smaller AOI for faster processing (SF peninsula)
    bbox = [-122.45, 37.75, -122.40, 37.80]
    
    search = catalog.search(
        collections=["sentinel-2-l2a"],
        bbox=bbox,
        datetime="2023-06-01/2023-08-31",
        query={"eo:cloud_cover": {"lt": 5}},
    )

    items = search.item_collection()
    print(f"Found {len(items)} items. Using the first cloud-free item.")
    item = items[0]

    # Stacking just the bands we need for RGB + NIR
    # Note: resolution=10 ensures all bands are at 10m
    cube = stackstac.stack(
        item, 
        assets=["B02", "B03", "B04", "B08"], # Blue, Green, Red, NIR
        bounds_latlon=bbox,
        epsg=3857,
        resolution=10 
    )

    # 2. Feature Engineering (NDVI & NDWI)
    print("Calculating spectral indices (NDVI & NDWI)...")
    red = cube.sel(band="B04")
    nir = cube.sel(band="B08")
    green = cube.sel(band="B03")
    
    # Squeeze and drop metadata coordinates to avoid concatenation issues
    def clean_da(da):
        keep_coords = ["x", "y", "band", "spatial_ref"]
        to_drop = [c for c in da.coords if c not in keep_coords]
        return da.squeeze().drop_vars(to_drop, errors="ignore")

    ndvi = clean_da((nir - red) / (nir + red)).expand_dims(band=["NDVI"])
    ndwi = clean_da((green - nir) / (green + nir)).expand_dims(band=["NDWI"])
    cube_squeezed = clean_da(cube)

    # Merge indices as new bands in the cube
    cube_with_indices = xr.concat([cube_squeezed, ndvi, ndwi], dim="band")
    cube_with_indices['band'] = ["B02", "B03", "B04", "B08", "NDVI", "NDWI"]

    # 3. Model Preparation
    print("Preparing features for K-Means...")
    # Convert to 2D array (pixels, features) and handle NaNs/NoData
    data_2d = cube_with_indices.transpose("y", "x", "band").to_numpy()
    h, w, b = data_2d.shape
    reshaped = data_2d.reshape(-1, b)
    
    # Simple NaN mask
    mask = np.all(np.isfinite(reshaped), axis=1)
    train_data = reshaped[mask]

    # 4. Clustering (K-Means)
    print(f"Running K-Means (3 clusters)...")
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(train_data)
    
    # Identify clusters based on mean spectral indices
    print("Labeling clusters based on spectral statistics...")
    cluster_labels = {}
    for i in range(3):
        cluster_mask = (clusters == i)
        # Get mean NDVI and NDWI for this cluster
        mean_ndvi = train_data[cluster_mask, 4].mean() # NDVI is index 4
        mean_ndwi = train_data[cluster_mask, 5].mean() # NDWI is index 5
        
        # Heuristic labeling
        if mean_ndwi > 0.1: # High water index
            label = "Water"
        elif mean_ndvi > 0.4: # High vegetation index
            label = "Vegetation"
        else:
            label = "Built-up/Barren"
        cluster_labels[i] = label
        print(f"  Cluster {i}: {label} (NDVI: {mean_ndvi:.2f}, NDWI: {mean_ndwi:.2f})")

    # Reconstruct image
    classified_img = np.full(h * w, -1, dtype=np.int32)
    classified_img[mask] = clusters
    classified_img = classified_img.reshape(h, w)

    # 5. Spatial Post-processing (Denoising)
    print("Sieve filtering (removing salt-and-pepper noise)...")
    denoised_img = rasterio.features.sieve(classified_img.astype(np.int32), size=20)

    # 6. Vectorization
    print("Vectorizing classification clusters...")
    shapes = rasterio.features.shapes(
        denoised_img.astype(np.int32), 
        mask=(denoised_img != -1),
        transform=cube.spec.transform
    )
    
    geoms = []
    cls_ids = []
    labels = []
    for s, v in shapes:
        geoms.append(shape(s))
        cluster_id = int(v)
        cls_ids.append(cluster_id)
        labels.append(cluster_labels.get(cluster_id, "Unknown"))
    
    gdf = gpd.GeoDataFrame(
        {"cluster_id": cls_ids, "label": labels}, 
        geometry=geoms, 
        crs=cube.crs
    )

    # 7. GeoParquet Export
    output_parquet = "land_cover_result.parquet"
    print(f"Exporting results to {output_parquet}...")
    gdf.to_parquet(output_parquet)

    # 8. Modern Analysis: DuckDB + GeoParquet
    print("\n--- 4. ANALYZING RESULTS WITH DUCKDB ---")
    try:
        con = duckdb.connect()
        con.install_extension("spatial")
        con.load_extension("spatial")
        
        # Calculate area statistics per label
        # We use ST_GeomFromWKB because geopandas exports to Parquet with WKB blobs by default
        # (or standard GeoParquet spec which DuckDB spatial can read)
        query = f"""
        SELECT 
            label, 
            COUNT(*) as feature_count,
            ROUND(SUM(ST_Area(geometry)), 2) as total_area_m2
        FROM read_parquet('{output_parquet}')
        GROUP BY label
        ORDER BY total_area_m2 DESC
        """
        
        stats = con.execute(query).df()
        print("Land Cover Statistics (Queried via DuckDB Spatial):")
        print(stats)
    except Exception as e:
        print(f"DuckDB analysis failed: {e}")

    # Visualization
    print("Generating 3-panel visualization (Imagery -> Raster ML -> Vector Data)...")
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    
    # Panel 1: Original RGB
    rgb = cube.sel(band=["B04", "B03", "B02"]).squeeze().to_numpy()
    rgb = np.moveaxis(rgb, 0, -1)
    rgb = (rgb / 3000).clip(0, 1)
    axes[0].imshow(rgb)
    axes[0].set_title("1. Original RGB")
    axes[0].axis('off')
    
    # Panel 2: Classification (Raster)
    cmap = plt.cm.get_cmap("viridis", 3)
    axes[1].imshow(denoised_img, cmap=cmap)
    axes[1].set_title("2. Denoised ML Clusters")
    axes[1].axis('off')

    # Panel 3: Vector Data (GeoPandas)
    # We use edgecolor='none' to avoid the "wireframe" look caused by thousands of tiny polygons
    gdf.plot(column='label', ax=axes[2], legend=False, cmap=cmap, edgecolor='none')
    axes[2].set_title("3. Final Vector (GeoParquet)")
    axes[2].axis('off')

    # Add Legend below the plots
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=cmap(i), label=f"{cluster_labels[i]}")
        for i in range(3)
    ]
    fig.legend(handles=legend_elements, loc='lower center', ncol=3, frameon=False)
    
    plt.tight_layout(rect=[0, 0.05, 1, 0.95])
    plt.savefig("classification_plot.png", dpi=150, bbox_inches='tight')
    print(f"Success! Result saved to {output_parquet} and 3-panel plot saved to classification_plot.png")

if __name__ == "__main__":
    main()
