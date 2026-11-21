# Title: Create Zarr Store
# Description: Generate dummy weather data and save it as Zarr
import xarray as xr
import numpy as np
import pandas as pd
import shutil
from pathlib import Path


def main():
    # Define Dimensions
    # 365 days, 100 latitudes, 100 longitudes
    times = pd.date_range("2024-01-01", periods=365)
    lats = np.linspace(-90, 90, 100)
    lons = np.linspace(-180, 180, 100)
    
    print("Generating dummy temperature data (365x100x100)...")
    # Random data
    temp_data = 15 + 8 * np.random.randn(365, 100, 100)
    
    # Create Xarray Dataset
    ds = xr.Dataset(
        data_vars=dict(
            temperature=(["time", "lat", "lon"], temp_data)
        ),
        coords=dict(
            lon=lons,
            lat=lats,
            time=times,
        ),
        attrs=dict(description="Dummy Weather Data for Zarr Tutorial")
    )
    
    # Define output path
    zarr_path = "weather_data.zarr"
    
    # Clean up if it exists
    if Path(zarr_path).exists():
        shutil.rmtree(zarr_path)
    
    print(f"Writing to {zarr_path}...")
    
    # Write to Zarr
    # We choose a chunk size. 
    # chunks={'time': 30} means we split the time dimension every 30 days.
    # This optimizes for accessing spatial slices over small time periods.
    ds.chunk({'time': 30, 'lat': 100, 'lon': 100}).to_zarr(zarr_path)
    
    print("Success! Check the folder structure.")

if __name__ == "__main__":
    main()