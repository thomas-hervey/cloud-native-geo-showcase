# Title: Zarr vs NetCDF Benchmark
# Description: Compare performance of multidimensional cloud-native storage.
import xarray as xr
import time
from pathlib import Path

def benchmark_read(path, format_name, engine=None):
    print(f"\n--- Benchmarking {format_name} ---")
    start_total = time.time()
    
    # Open dataset
    if format_name == "Zarr":
        ds = xr.open_zarr(path, chunks={})
    else:
        ds = xr.open_dataset(path, engine=engine, chunks={})
    
    print(f"Dataset opened (lazyly) in {time.time() - start_total:.4f}s")
    
    # Operation: Mean temperature for a specific spatial area across all time
    # This involves reading all chunks in the time dimension
    start_calc = time.time()
    result = ds.temperature.mean(dim="time").compute()
    calc_time = time.time() - start_calc
    
    print(f"Mean temperature over time calculated in {calc_time:.4f}s")
    return calc_time

def main():
    data_dir = Path("data")
    nc_path = data_dir / "sample_climate.nc"
    zarr_path = data_dir / "sample_climate.zarr"
    
    if not nc_path.exists() or not zarr_path.exists():
        print("Error: Sample files not found. Run create_zarr.py first.")
        return

    # Benchmark NetCDF
    nc_time = benchmark_read(nc_path, "NetCDF", engine="h5netcdf")
    
    # Benchmark Zarr
    zarr_time = benchmark_read(zarr_path, "Zarr")
    
    print("\n--- SUMMARY ---")
    print(f"NetCDF Time: {nc_time:.4f}s")
    print(f"Zarr Time:   {zarr_time:.4f}s")
    print(f"Zarr is {nc_time / zarr_time:.1f}x faster for this operation")
    
    print("\nWhy did this happen?")
    print("1. Chunks: Zarr is stored as small, independent files (chunks).")
    print("2. Parallelism: Dask read multiple Zarr chunks in parallel.")
    print("3. HTTP-Friendly: In a real cloud environment, Zarr chunks mapping")
    print("   to S3 objects results in much higher IO throughput than a")
    print("   single monolithic NetCDF file.")

if __name__ == "__main__":
    main()
