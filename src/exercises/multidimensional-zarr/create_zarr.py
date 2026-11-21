# Title: Create Zarr and NetCDF Data
# Description: Generate a synthetic climate dataset and compare storage formats.
import xarray as xr
import numpy as np
import pandas as pd
import os
import shutil
from pathlib import Path

def main():
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    nc_path = data_dir / "sample_climate.nc"
    zarr_path = data_dir / "sample_climate.zarr"
    
    # 1. Generate Synthetic Climate Data
    # 1000 days, 100x100 grid
    print("Generating synthetic data (1000 days, 100x100)...")
    times = pd.date_range("2010-01-01", periods=1000)
    lats = np.linspace(-90, 90, 100)
    lons = np.linspace(-180, 180, 100)
    
    temp_data = 15 + 10 * np.random.randn(1000, 100, 100)
    
    ds = xr.Dataset(
        data_vars=dict(
            temperature=(["time", "lat", "lon"], temp_data)
        ),
        coords=dict(
            time=times,
            lat=lats,
            lon=lons
        ),
        attrs=dict(description="Synthetic Climate Data for Benchmarking")
    )
    
    # 2. Save as NetCDF
    print(f"Saving to NetCDF: {nc_path}")
    # We use h5netcdf engine for scalability
    ds.to_netcdf(nc_path, engine="h5netcdf")
    
    # 3. Save as Zarr with specific chunking
    if zarr_path.exists():
        shutil.rmtree(zarr_path)
    
    print(f"Saving to Zarr: {zarr_path}")
    # Chunks of 100 in time dimension to optimize for time-series analysis
    ds.chunk({"time": 100, "lat": 100, "lon": 100}).to_zarr(zarr_path)
    
    print("\nSuccess! Files created.")
    print(f"NetCDF Size: {nc_path.stat().st_size / (1024*1024):.2f} MB")
    
    # Calculate Zarr size (directory of files)
    zarr_size = sum(f.stat().st_size for f in zarr_path.rglob('*') if f.is_file())
    print(f"Zarr Total Size: {zarr_size / (1024*1024):.2f} MB")

if __name__ == "__main__":
    main()
