# Cloud Native Geo Tutorial - Practical Exercises
<!-- last_sync_verify: 2026-04-07 -->

This directory contains the hands-on coding exercises for the Cloud Native
Geospatial tutorial.

## Setup

We recommend using a single shared **uv** environment for all exercises to avoid
managing 10+ virtual environments.

### 1. Initialize Environment

Currently, the dependencies are managed in `stac/pyproject.toml` (Legacy). We
recommend creating a new one in this root `exercises` folder.

```bash
# Initialize new project
uv init
# Add dependencies (see Concept section)
uv add rasterio xarray ...
```

### 2. Organizing Your Work

Your `src/exercises` directory should look like this. We recommend creating a
folder for each module as you progress.

```filetree
src/exercises/
├── stac/
├── cog/
│   ├── create_cog.py
│   └── read_cog.py
├── zarr/
└── pyproject.toml
```

### 3. Workflow

For each exercise (e.g., "COG"):

1. **Read the Concept**: Open the relevant concept markdown file.
2. **Code**: Create python scripts (e.g., `create_cog.py`) in your
   `src/exercises/cog/` folder.
3. **Run**: Execute them using `uv run`.

   ```bash
   uv run cog/create_cog.py
   ```

## Common Dependencies

You will frequently use:

- `rasterio` and `rio-cogeo` (Raster/COG)
- `xarray` and `zarr` (N-D Arrays)
- `geopandas` and `pyarrow` (Vectors)
- `pystac` and `pystac-client` (Metadata/Search)
