# Title: STAC Geospatial Workflow
# Description: Create a complete geospatial workflow using STAC for NDVI calculation
import pystac_client
import planetary_computer
import matplotlib.pyplot as plt
import rioxarray
import numpy as np
import geopandas as gpd
from shapely.geometry import box
import os

def main():
    print("Starting STAC-powered geospatial workflow...")
    
    # Define an area of interest (San Francisco Bay Area)
    aoi_bounds = [-122.5, 37.5, -122.0, 38.0]  # [minx, miny, maxx, maxy]
    aoi_geometry = box(*aoi_bounds)
    
    print(f"Area of interest: San Francisco Bay Area {aoi_bounds}")
    
    # Connect to Microsoft Planetary Computer STAC API
    print("Connecting to Microsoft Planetary Computer STAC API...")
    catalog = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace
    )
    
    # Search for Landsat 8 scenes
    print("Searching for Landsat 8 scenes with low cloud cover...")
    search = catalog.search(
        collections=["landsat-8-c2-l2"],
        bbox=aoi_bounds,
        datetime="2021-06-01/2021-07-01",
        query={"eo:cloud_cover": {"lt": 10}}
    )
    
    # Get the first item
    items = list(search.get_items())
    if not items:
        print("No items found matching the search criteria.")
        return
    
    item = items[0]
    print(f"Processing item: {item.id} from {item.datetime}")
    
    # Access the red and NIR bands for NDVI calculation
    red_asset = item.assets.get("SR_B4")
    nir_asset = item.assets.get("SR_B5")
    
    if not red_asset or not nir_asset:
        print("Required bands not found in the item assets.")
        return
    
    # Open the assets as rioxarray DataArrays
    print("Loading and clipping red band...")
    # Masking and scaling are crucial for Landsat C2 L2 data
    red = rioxarray.open_rasterio(red_asset.href, masked=True)
    print("Loading and clipping NIR band...")
    nir = rioxarray.open_rasterio(nir_asset.href, masked=True)

    # 1. Reproject the AOI to match the raster CRS
    # This is key to fixing the "tiny plot" visualization issue
    aoi_gdf = gpd.GeoDataFrame(geometry=[aoi_geometry], crs="EPSG:4326")
    aoi_reprojected = aoi_gdf.to_crs(red.rio.crs)
    
    # 2. Clip the data to our AOI to speed up processing and improve plot
    red_clipped = red.rio.clip(aoi_reprojected.geometry, aoi_reprojected.crs)
    nir_clipped = nir.rio.clip(aoi_reprojected.geometry, aoi_reprojected.crs)

    # 3. Apply Landsat Collection 2 Scale and Offset
    # Reflectance = DN * 0.0000275 - 0.2
    red_scaled = red_clipped * 0.0000275 - 0.2
    nir_scaled = nir_clipped * 0.0000275 - 0.2
    
    # Calculate NDVI
    print("Calculating NDVI (Normalized Difference Vegetation Index)...")
    ndvi = (nir_scaled - red_scaled) / (nir_scaled + red_scaled)
    
    # Plot the results
    print("Generating visualizations...")
    # Reproject to WGS84 for display so coordinates are in degrees
    red_plot = red_scaled.rio.reproject("EPSG:4326")
    ndvi_plot = ndvi.rio.reproject("EPSG:4326")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7))
    
    # Plot the red band
    red_plot.isel(band=0).plot.imshow(ax=ax1, cmap='Reds', vmin=0, vmax=0.3)
    aoi_gdf.boundary.plot(ax=ax1, color='blue', linewidth=2)
    ax1.set_title("Red Band (Reflectance) - Degrees")
    
    # Plot the NDVI
    ndvi_plot.isel(band=0).plot.imshow(ax=ax2, cmap='RdYlGn', vmin=-1, vmax=1)
    aoi_gdf.boundary.plot(ax=ax2, color='black', linewidth=2)
    ax2.set_title("NDVI (Vegetation Index) - Degrees")
    
    # Zoom into the AOI extent
    for ax in [ax1, ax2]:
        ax.set_xlim(aoi_bounds[0], aoi_bounds[2])
        ax.set_ylim(aoi_bounds[1], aoi_bounds[3])

    
    plt.tight_layout()
    output_file = 'ndvi_analysis.png'
    plt.savefig(output_file)
    plt.close()
    
    print(f"Analysis complete! Results saved as '{output_file}'")
    
    # Calculate some basic statistics on the NDVI
    # Use .min() / .max() ignoring NaNs
    print("\nNDVI Statistics:")
    print(f"  Mean NDVI: {float(ndvi.mean().values):.4f}")
    print(f"  Min NDVI:  {float(ndvi.min().values):.4f}")
    print(f"  Max NDVI:  {float(ndvi.max().values):.4f}")
    
    # Interpret NDVI values
    print("\nNDVI Interpretation:")
    print("  < 0: Water, buildings, roads, bare soil")
    print("  0-0.2: Sparse vegetation")
    print("  0.2-0.4: Moderate vegetation")
    print("  0.4-0.6: Dense vegetation")
    print("  > 0.6: Very dense vegetation")
    
    print("\nThis workflow demonstrates how STAC enables:")
    print("1. Discovery of relevant satellite imagery")
    print("2. Direct access to specific bands needed for analysis")
    print("3. Integration with geospatial analysis libraries")
    print("4. Reproducible scientific workflows")

if __name__ == "__main__":
    main()