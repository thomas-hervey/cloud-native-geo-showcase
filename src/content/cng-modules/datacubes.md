## Overview

In the previous module, we managed vast collections of vector data using
**Apache Iceberg**. Now, we turn our attention back to raster data—specifically,
how to manage **collections of images** as a single multi-dimensional object.

A **Datacube** is a representation of geospatial data where different datasets
(like Sentinel-2, Landsat, or weather models) are aligned into a common
coordinate system and time axis. Datacubes make it straightforward to ask
questions like "how did vegetation change over this area across an entire year?"
without manually wrangling individual images.

## Key Concepts

### 1. The Datacube Abstraction

A geospatial datacube organizes raster imagery as an N-dimensional array with
labeled axes: typically time, band, Y (latitude/northing), and X
(longitude/easting). This structure lets you slice, aggregate, and compute
across any combination of dimensions using the same xarray syntax — no matter
how many images or bands are involved.

### 2. Stacking Imagery

Raw STAC items arrive with mismatched coordinate systems, different spatial
resolutions, and pixel grids that don't align. Stacking aligns all of them onto
a common grid by reprojecting and snapping pixels to a consistent reference.
The `stackstac` library automates this process, turning a list of STAC items
into a single 4D `xarray.DataArray` that is ready for analysis.

### 3. STAC-to-Cube Pipeline

The typical workflow starts with a STAC API search, filters by cloud cover and
date, then passes the resulting items to `stackstac.stack()`. Because
`stackstac` uses Dask internally, the cube is built lazily — no data is
downloaded until you call `.compute()` or `.plot()`. This means you can build
and inspect the full cube structure before committing to any network I/O.

### From "Assets" to "Cubes"

When you search a STAC API, you get a "Collection of Items." Each item has
assets (bands like Red, Green, NIR) but they might:

- Be in different Coordinate Reference Systems (CRS).
- Have different spatial resolutions (10m vs 60m).
- Be slightly shifted from each other.

To analyze them together (e.g., to see how vegetation changes over a year), you
need to **align** them.

## Key Tool: stackstac

`stackstac` is a Python library that turns a list of STAC items into a 4D
`xarray.DataArray`. It handles the heavy lifting of:

1. **Reprojection**: Warping images to a matching CRS.
2. **Alignment**: Snapping pixels to a consistent grid.
3. **Laziness**: It uses **Dask** under the hood, so it doesn't download any
   data until you actually perform a calculation.

### The 4 Dimensions

A typical geospatial datacube has four axes:

1. **Time**: When the image was taken.
2. **Band**: Which spectral band (Red, Blue, NIR, etc).
3. **Y**: Latitude or Northing.
4. **X**: Longitude or Easting.

## Practical Exercises

One exercise builds a Sentinel-2 datacube over San Francisco using `stackstac`,
calculates mean NDVI across a time range, and saves a visualization — showing
the full STAC-to-cube-to-analysis pipeline in a single script.



## Next Steps

Now that you can work with high-level multidimensional arrays, you are ready to
tackle **Cloud Storage** patterns, where you'll learn how to optimize access to
these massive datasets directly from object storage (S3/Azure/GCS).
