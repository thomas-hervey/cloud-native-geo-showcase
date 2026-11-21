# Title: Create and Analyze Datacubes
# Description: Use stackstac to align multi-temporal Sentinel-2 imagery into a 4D array
import pystac_client
import planetary_computer
import stackstac
import matplotlib.pyplot as plt
import xarray as xr
import os

def main():
    # 1. Search for data
    print("Searching for cloud-free Sentinel-2 items...")
    catalog = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace,
    )

    # Area of Interest (SF Peninsula)
    bbox = [-122.45, 37.75, -122.40, 37.80]
    
    search = catalog.search(
        collections=["sentinel-2-l2a"],
        bbox=bbox,
        datetime="2023-05-01/2023-09-30",
        query={"eo:cloud_cover": {"lt": 5}},
    )

    items = search.item_collection()
    print(f"Found {len(items)} items")

    if len(items) == 0:
        print("No items found. Try a broader search.")
        return

    # 2. Create the Datacube
    # stackstac.stack handles the alignment/reprojection to Web Mercator (EPSG:3857)
    print("Stacking items into a datacube...")
    cube = stackstac.stack(
        items, 
        assets=["B04", "B08"], 
        bounds_latlon=bbox,
        epsg=3857 
    )

    # 3. Calculate NDVI (Normalized Difference Vegetation Index)
    # This is a lazy operation - no data is downloaded yet!
    print("Calculating NDVI across the time series...")
    red = cube.sel(band="B04").astype("float")
    nir = cube.sel(band="B08").astype("float")
    
    ndvi = (nir - red) / (nir + red)

    # 4. Temporal Reduction (Mean)
    # We collapse the 'time' dimension by taking the average
    print("Reducing time dimension (Mean)...")
    ndvi_mean = ndvi.mean(dim="time")

    # 5. Execution and Visualization
    # Calling .plot() or .compute() triggers the parallel range requests
    print("Executing computation and generating plot...")
    plt.figure(figsize=(10, 8))
    ndvi_mean.plot(cmap="RdYlGn", vmin=0, vmax=1)
    plt.title("Sentinel-2 Mean NDVI (Summer 2023) - SF")
    
    output_path = "ndvi_datacube.png"
    plt.savefig(output_path)
    print(f"Success! Analysis complete. Saved plot to {output_path}")

if __name__ == "__main__":
    main()