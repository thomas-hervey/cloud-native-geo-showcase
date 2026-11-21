# Title: Read Zarr
# Description: Lazy-load Zarr data and perform a calculation
import xarray as xr
import matplotlib.pyplot as plt

def main():
    zarr_path = "weather_data.zarr"
    
    print(f"Opening {zarr_path}...")
    
    # Open the dataset
    # chunks={} argument is important! It implies using Dask for lazy loading.
    ds = xr.open_zarr(zarr_path, chunks={})
    
    print("Dataset Info (Lazy Loaded):")
    print(ds)
    
    # Example 1: Mean temperature for January
    # Because of lazy loading, no data is read yet.
    jan_mean = ds.sel(time="2024-01").temperature.mean()
    print(f"\nExample 1: January Mean Temperature: {jan_mean.compute().values:.2f} deg")
    
    # Example 2: Spatial Selection (Nearest Neighbor)
    # Get temperature for San Francisco (approx 37.7, -122.4) at a specific time
    sf_temp = ds.sel(lat=37.7, lon=-122.4, method="nearest").temperature.isel(time=0)
    print(f"Example 2: SF Temp on Day 1: {sf_temp.compute().values:.2f} deg")

    # Example 3: Range Filtering
    # What percentage of "pixels" in January were over 25 degrees
    hot_days = ds.sel(time="2024-01").temperature > 25
    hot_pct = hot_days.mean().compute() * 100
    print(f"Example 3: Percentage of 'hot' pixels (>25deg) in Jan: {hot_pct.values:.2f}%")

    # Example 4: Visualization (Spatial Slice)
    print("\nExample 4: Generating spatial plot for Day 1...")
    plt.figure(figsize=(10, 5))
    ds.temperature.isel(time=0).plot(cmap="RdYlBu_r")
    plt.title("Temperature Map (Day 1)")
    plt.savefig("zarr_map.png")
    print("Saved 'zarr_map.png'")

    # Example 5: Visualization (Time Series at a point)
    print("Example 5: Generating time-series for SF...")
    plt.figure(figsize=(10, 5))
    ds.sel(lat=37.7, lon=-122.4, method="nearest").temperature.plot()
    plt.title("Temperature over Time at SF")
    plt.savefig("zarr_timeseries.png")
    print("Saved 'zarr_timeseries.png'")

    print("\nNote: In all examples, Xarray only read the specific chunks needed!")

if __name__ == "__main__":
    main()