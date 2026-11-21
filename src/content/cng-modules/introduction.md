## Overview

Cloud-native geospatial (CNG) refers to geospatial data formats, software, and
workflows designed to take advantage of cloud computing capabilities. These
technologies enable efficient storage, access, and processing of geospatial data
at scale, opening up new possibilities for Earth observation, climate science,
and a range of other applications.

## Key Concepts

### What makes geospatial data "cloud-native"?

Cloud-native geospatial formats and technologies typically share these
characteristics:

1. **Decomposable**: Data can be broken down into smaller, independent chunks
2. **Directly accessible**: Specific portions of data can be accessed without
   downloading entire files
3. **Cloud-optimized**: Designed for distributed storage and processing in cloud
   environments
4. **Open standards**: Based on open specifications that promote
   interoperability
5. **Format-aware**: Tools understand the internal structure of data formats

### Core technologies in the ecosystem

The cloud-native geospatial ecosystem includes several key technologies:

- **STAC (SpatioTemporal Asset Catalog)**: A specification for cataloging
  geospatial data
- **COG (Cloud Optimized GeoTIFF)**: A format for efficient access to geospatial
  raster data
- **Zarr**: A format for storing and accessing n-dimensional arrays
- **GeoParquet**: A columnar storage format for geospatial vector data
- **Apache Iceberg**: A table format for large analytical datasets with
  geospatial support

## Benefits of Cloud-Native Geospatial

- **Scalability**: Process petabyte-scale datasets without downloading
- **Cost efficiency**: Pay only for the compute and storage you need
- **Performance**: Access only the specific data you need, when you need it
- **Collaboration**: Share data through standardized formats and APIs
- **Democratization**: Lower barriers to entry for working with geospatial data

## From Fundamentals to Projects

The concepts in this tutorial (STAC, COG, Zarr, GeoParquet) are the "atoms" of
modern cloud-native systems. Throughout the curriculum, you'll see how these are
combined into larger projects:

- **Spatial Eval**: [Interactive Dashboard](/spatial-eval) &
  [Learning Module](/cng-modules/llm-geo-knowledge-eval). An experiment
  framework for benchmarking LLM geographic knowledge against authoritative
  ground-truth data.
- **Scout**: [Live Lab](/scout/lab) &
  [Learning Module](/cng-modules/scout-intro). A "Chat-to-Map" application that
  uses Agentic GIS and LLMs to interact with geospatial data. **NOTE: This
  feature is currently gated**

## Learning Resources

- [Cloud-Native Geospatial Foundation](https://cloudnativegeo.org/)
- [Planet's Cloud-Native Geospatial Outreach](https://developers.planet.com/docs/planetschool/cloudnative/)
- [Development Seed's Cloud-Native Geospatial Guide](https://developmentseed.org/blog/2022-05-11-cng-guide)

## Practical Exercises

The best way to learn cloud-native geospatial is to write code. Each module in
this curriculum ends with hands-on exercises using real datasets and tools like
PySTAC, rasterio, xarray, and DuckDB. Use **uv** to manage your Python
dependencies and run exercises from the shared `src/exercises/` environment.

*Exercise files coming soon.*

Browse the **Practical Implementation** section below when exercises are available.

## Related Sessions from CNG Conference

- "Data Gravity Shapes the Architecture of Cloud Native Geospatial" by Howard
  Butler [Hobu, Inc]
- "Cloud-Native Geospatial and ArcGIS" by David Wright [Esri]
- "Minimum Viable CNG" by Brandon Liu [Protomaps]
