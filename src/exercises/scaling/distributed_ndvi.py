import pystac_client
import stackstac
import dask.distributed
from dask.distributed import Client
import time
import xarray as xr

def main():
    print("--- 1. INITIALIZING LOCAL DASK CLUSTER ---")
    # Start a local cluster with some default workers
    client = Client(n_workers=4, threads_per_worker=2, memory_limit='2GB')
    print(f"Dask Dashboard available at: {client.dashboard_link}")

    print("\n--- 2. SEARCHING FOR DATA ---")
    catalog = pystac_client.Client.open("https://earth-search.aws.element84.com/v1")
    
    # We'll grab a few scenes of San Francisco to simulate a time-series
    bbox = [-122.51, 37.70, -122.35, 37.83]
    search = catalog.search(
        collections=["sentinel-2-l2a"],
        bbox=bbox,
        datetime="2023-01-01/2023-06-30",
        query={"eo:cloud_cover": {"lt": 10}}
    )
    items = list(search.get_items())
    print(f"Found {len(items)} items.")

    print("\n--- 3. CREATING LAZY DATACUBE WITH CHUNKS ---")
    # THE SECRET SAUCE: chunksize
    # This tells stackstac/xarray/dask how to break the data into parallel tasks
    cube = stackstac.stack(
        items,
        assets=["red", "nir"], 
        bounds_latlon=bbox,
        epsg=32610,
        resolution=10,
        chunksize=1024 # 1024x1024 pixel chunks
    )
    
    print(f"Lazy Cube Shape: {cube.shape} (Time: {cube.time.item})")
    print(f"Number of Dask Chunks: {len(cube.chunks[0]) * len(cube.chunks[1]) * len(cube.chunks[2])}")

    print("\n--- 4. CALCULATING NDVI (LAZILY) ---")
    # This operation finishes instantly because NO work is actually done yet
    start_lazy = time.time()
    red = cube.sel(band="red").astype("float32")
    nir = cube.sel(band="nir").astype("float32")
    
    # Handle zeros in denominator and nodata (0)
    denominator = nir + red
    ndvi = xr.where(denominator != 0, (nir - red) / denominator, 0)
    
    # Clip to valid NDVI range [-1, 1]
    ndvi = ndvi.clip(-1, 1)
    
    mean_ndvi = ndvi.mean(dim=["x", "y"])
    end_lazy = time.time()
    print(f"Lazy computation graph built in {end_lazy - start_lazy:.4f} seconds")

    print("\n--- 5. TRIGGERING COMPUTE (PARALLEL EXECUTION) ---")
    print("Sending tasks to Dask workers...")
    start_compute = time.time()
    # This is where the actual HTTP requests and math happen
    result = mean_ndvi.compute()
    end_compute = time.time()
    
    print(f"\nTime Series NDVI Means:")
    for t, val in zip(result.time.values, result.values):
        print(f"  {str(t)[:10]}: {val:.4f}")
    
    print(f"\nComputation completed in {end_compute - start_compute:.4f} seconds")

    print("\n--- 6. VISUALIZING RESULTS ---")
    import matplotlib.pyplot as plt
    
    plt.figure(figsize=(10, 5))
    result.plot(marker='o', linestyle='-', color='forestgreen')
    plt.title("San Francisco Regional Mean NDVI (2023 Time Series)")
    plt.ylabel("Mean NDVI")
    plt.xlabel("Date")
    plt.grid(True, alpha=0.3)
    
    output_png = "ndvi_timeseries.png"
    plt.savefig(output_png, bbox_inches='tight', dpi=150)
    print(f"Time-series plot saved to: {output_png}")
    
    client.close()
    print("\nDone! Notice how we processed multiple timesteps in parallel.")

if __name__ == "__main__":
    main()
