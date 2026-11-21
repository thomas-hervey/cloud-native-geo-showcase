# Zarr Exercises

This folder contains the practical exercises for native Zarr data handling.

## Setup

Ensure you have the shared environment set up.

```bash
# Verify dependencies
uv add xarray zarr dask netcdf4 pandas
```

## Your Task

1. Create `create_zarr.py`: Generate specific dummy weather data and save it as
   a Zarr store.
2. Create `read_zarr.py`: Use `xarray` to lazily load and compute statistics
   from the store.

Refer to the [Zarr lesson content](/cng-modules/zarr) for the code snippets.
