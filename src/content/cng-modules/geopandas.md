## Overview

GeoPandas is the backbone library for working with vector geodata in Python. It combines the power of **pandas** DataFrames with spatial capabilities from **Shapely** and **Fiona**, making it the standard tool for loading, transforming, visualizing, and exporting geospatial vector data. You've already used GeoPandas across several modules as a supporting library — this module teaches it as a **standalone skill**, from first principles through real-world spatial analysis.

## Key Concepts

### 1. GeoDataFrame — Spatial Extension of pandas

A `GeoDataFrame` is a pandas DataFrame with one special column: `geometry`. That column holds Shapely geometry objects (Point, LineString, Polygon, etc.) and carries a coordinate reference system (CRS) attribute. All spatial operations — joins, filters, area calculations — are dispatched through that geometry column, keeping the familiar pandas interface intact.

### 2. CRS Management — Projection and Transformation

Every GeoDataFrame has a CRS that defines how its coordinates map to the Earth's surface. Working with multiple datasets requires that they share the same CRS; `gdf.to_crs(epsg=3857)` reprojects in a single call. Failing to manage CRS is the most common source of "data looks right but is offset by kilometers" bugs in geospatial Python.

### 3. Spatial Operations — sjoin, dissolve, overlay

GeoPandas exposes set-theoretic and relational spatial operations directly: `sjoin` performs point-in-polygon or intersects joins between two GeoDataFrames; `dissolve` merges geometries by an attribute (analogous to `groupby + union`); `overlay` computes intersection, union, or difference between polygon layers. These three operations cover the majority of real-world vector analysis workflows.

## Learning Objectives

By the end of this module you'll be able to:

1. Load geodata from any common format (GeoJSON, Shapefile, GeoParquet, WKB/WKT)
2. Understand CRS (coordinate reference systems) and when/how to reproject
3. Perform spatial joins (point-in-polygon, intersects, within)
4. Calculate areas, lengths, centroids, and distances
5. Create static and interactive maps using matplotlib and Folium
6. Combine GeoPandas with DuckDB and Shapely for real analysis

## Tutorial Credit

The tutorial notebooks in this module are based on the excellent video series by
**Matt Forester** (YouTube: [GeoPandas Tutorial](https://www.youtube.com/watch?v=0mWgVVH_dos)).
The six provided notebooks (`geopandas-1.ipynb` through `geopandas-6.ipynb`) follow
his curriculum. An additional personal notes notebook (`00_personal_notes.ipynb`)
captures annotations and extensions added while working through the series.

## Dataset: New York City

All exercises use publicly available New York City datasets:

| File | Source | Description |
|---|---|---|
| `custom_nyc_neighborhoods.geojson` | NYC Open Data / Pedia Cities | NYC neighborhood boundary polygons |
| `custom_pedia_cities_nyc.geojson` | Pedia Cities | Alternative neighborhood classifications |
| `neighborhood_access_index.geojson` | NYU Furman Center | Walkability and transit access scores per neighborhood |
| `New York City Bike Routes_20241223.geojson` | NYC Open Data | All bike lane and route geometries |
| `Parks Properties_20241223.geojson` | NYC Open Data | Park polygon boundaries citywide |
| `nyc_subway_entrances/` | NYC Open Data | Point features for all subway entrance locations |
| `SchoolPoints_APS_2024_08_28 (1)/` | NYC DOE | Public school locations |

> **Note**: `es_cn.parquet` (elementary school + census data) and
> `internet-speeds.parquet` are available locally but excluded from git (large
> files). See `data/README.md` for download instructions if needed.

## Practical Exercises

Work through six progressive notebooks covering GeoDataFrame basics, CRS management, spatial joins, geometry operations, real-world bike/park analysis, and export to other tools — all using NYC open datasets.



## Connections to Other Modules

- (Vector Formats): Uses GeoPandas to read/write GeoParquet and compare with GeoJSON/FlatGeobuf
- (Iceberg): WKB → GeoPandas conversion for visualization
- (Fast Legacy): `pyogrio` + GeoPandas for high-speed FileGDB ingest
- (Scout ETL): DuckDB results → GeoPandas → lonboard visualization
- (LLM Eval): GeoPandas for computing IoU and Hausdorff metrics on LLM-generated polygons

## Key Packages

`uv add geopandas matplotlib folium mapclassify pyogrio shapely`

| Package | Purpose |
|---|---|
| `geopandas` | Core GeoDataFrame: load, transform, join, export |
| `shapely` | Geometry objects: Point, LineString, Polygon, operations |
| `matplotlib` | Static map rendering, choropleth maps |
| `folium` | Interactive Leaflet.js maps from Python |
| `mapclassify` | Classification schemes for choropleth maps (quantile, jenks, etc.) |
| `pyogrio` | Fast Shapefile/FileGDB/GeoPackage reader backend |

## Further Reading

- [GeoPandas User Guide](https://geopandas.org/en/stable/docs/user_guide.html)
- [Shapely Manual](https://shapely.readthedocs.io/en/stable/manual.html)
- [NYC Open Data Portal](https://opendata.cityofnewyork.us/)
