## Overview

STAC is a specification designed to standardize how geospatial assets are
exposed online and queried. A 'spatiotemporal asset' is any file that represents
information about the earth captured in a certain space and time.

## Key Concepts

### STAC Items

A STAC Item is a GeoJSON feature with additional metadata properties and links.
It represents a single spatiotemporal asset, such as a satellite image, and
includes:

- A geometry describing the spatial extent of the asset
- A timestamp or temporal extent for when the data was captured
- Asset links pointing to the actual data files
- Properties providing additional context and metadata

### STAC Catalogs

A STAC Catalog is a JSON object that contains links to STAC Items or other
catalogs. It provides a way to organize and navigate through collections of
spatiotemporal assets.

### STAC Collections

A STAC Collection is a specialization of a catalog that provides additional
information about a group of related STAC Items, such as common properties,
temporal and spatial extents, and licensing information.

### STAC API

The STAC API specification extends the core STAC specification to provide a
RESTful API for querying and accessing spatiotemporal assets. It enables
powerful filtering capabilities based on spatial, temporal, and other metadata
properties.

## Why STAC Matters for Cloud-Native Geospatial

STAC addresses several key challenges in the geospatial data ecosystem:

1. **Discoverability**: Makes it easier to find relevant geospatial data across
   different providers
2. **Interoperability**: Provides a common language for describing geospatial
   assets
3. **Scalability**: Enables efficient querying of large catalogs of geospatial
   data
4. **Integration**: Facilitates the integration of geospatial data into
   cloud-based workflows

## Common STAC Extensions

STAC Extensions allow the core specification to be extended for specific use
cases:

- **EO Extension**: Adds properties specific to Earth Observation data
- **SAR Extension**: Adds properties specific to Synthetic Aperture Radar data
- **Scientific Extension**: Adds properties for scientific datasets
- **Projection Extension**: Adds properties related to the spatial reference
  system

## Tools and Libraries

- **PySTAC**: Python library for working with STAC
- **STAC Browser**: Web application for browsing STAC catalogs
- **stac-fastapi**: Framework for building STAC APIs in Python
- **STAC Index**: Registry of public STAC catalogs

## Public STAC Catalogs

- [Microsoft Planetary Computer](https://planetarycomputer.microsoft.com/)
- [Earth Search (Element 84)](https://earth-search.aws.element84.com/v1)
- [NASA CMR STAC API](https://cmr.earthdata.nasa.gov/stac/)
- [Google Earth Engine STAC Catalog](https://earthengine-stac.storage.googleapis.com/catalog/catalog.json)

## Practical Exercises

Three exercises walk you through the full STAC lifecycle: building a catalog
from scratch with PySTAC, querying a public API for satellite imagery, and
wiring that imagery into a real NDVI analysis workflow.



## Additional Resources

For more in-depth learning about STAC, check out these resources:

- [STAC Index Learning Resources](https://stacindex.org/learn)
- [PySTAC Documentation](https://pystac.readthedocs.io/)
- [STAC Tutorials on GitHub](https://github.com/radiantearth/stac-tutorials)
- [STAC API Specification](https://github.com/radiantearth/stac-api-spec)
- [STAC Browser](https://radiantearth.github.io/stac-browser/)

## Related Sessions & Community Updates

### Foundational Concepts

- **[Introduction to STAC](https://www.youtube.com/watch?v=hO7W5z6YF2M)** by
  Matthew Hanson [Element 84]
<!-- TODO: Verify this YouTube ID is the correct STAC<>Zarr session video -->
- **[STAC <> Zarr](https://www.youtube.com/watch?v=XvK_5m_qO_Y)** by Julia
  Signell [Element 84]
- **[Right-sizing STAC: An exploration of STAC API backends, including stac-geoparquet](https://www.youtube.com/watch?v=6P644V6y_q8)**
  by Pete Gadomski [Development Seed]

### Modern CNG Technical Sessions (2025-2026)

- **[STAC as an OGC Community Standard](https://www.ogc.org/standards/stac)**:
  In 2025, STAC was officially adopted as an OGC Community Standard, solidifying
  its place in global geospatial infrastructure.
- **STAC + Zarr Community Sprint 2025**:
  Key findings on representing massive multidimensional arrays in STAC catalogs.
- **Cloud-Native Geospatial Forum 2026**:
  Join the community in Snowbird, Utah (Oct 2026) for the latest on GeoParquet,
  STAC, and Iceberg implementation.

_For more, browse the full
[CNG Conference archive](https://conference.cloudnativegeo.org)._
