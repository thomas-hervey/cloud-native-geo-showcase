<!-- TODO: Review for expansion - does this module feel too short compared to STAC/Zarr? -->

## Overview

A Cloud Optimized GeoTIFF (COG) is a regular GeoTIFF file, aimed at being hosted
on a HTTP file server, with an internal organization that enables more efficient
workflows on the cloud. It does this by leveraging the ability of clients
issuing HTTP range requests to ask for just the parts of a file they need.

## Key Concepts

### 1. Internal Tiling

Instead of storing the image data line-by-line (stripes), a COG stores data in
small square tiles (usually 256x256 or 512x512 pixels). This allows a client to
read only the specific area of interest without reading the entire row of data.

### 2. Overviews

COGs include internal downsampled versions of the image (pyramids). If you zoom
out effectively to see the whole image, the client can just read the small,
low-resolution overview instead of downloading the massive full-resolution data
and downsampling it on the fly.

### 3. Header Structure

The key metadata (IFD - Image File Directory) is moved to the _beginning_ of the
file. This means a client can make one small initial HTTP request to learn
everything about the file structure (where the tiles are, what the projection
is) and then make subsequent targeted requests for the data.

## Why COG is Important

- **Legacy Compatible**: It is still just a TIFF. Any software that reads TIFFs
  can read a COG (it just might not be optimized).
- **Streaming**: You don't need to download the file to see it. QGIS, GDAL, and
  web maps can stream it directly.
- **Partial Access**: If you only need a small 100x100 pixel chip from a 100GB
  image, you only download those few kilobytes.

## Tools and Libraries

- **GDAL**: The core library behind almost all geospatial raster tools.
- **rio-cogeo**: A Python plugin for Rasterio specifically for creating and
  validating COGs.
- **Titiler**: A dynamic Tiler capable of reading COGs on the fly.

## Practical Exercises

Two exercises cover the full COG workflow: converting a standard GeoTIFF to a
COG using `rio-cogeo`, then reading a partial window from the resulting file to
see exactly how range requests reduce data transfer.



## What happened?

1. **Preparation**: `rio-cogeo` re-organized the pixels into 512x512 tiles and
   added overviews (zoom levels).
2. **Streaming**: When `rasterio.open` read the window, it calculated exactly
   which tiles were needed (just the top-left one) and read only those bytes. If
   this file were 100GB on S3, the script would still run instantly because it
   wouldn't download the other 99.9GB.

## Next Steps

Now that we understand how to _optimize_ rasters for the cloud, let's look at
the cloud-native format for multi-dimensional data: **Zarr**.
