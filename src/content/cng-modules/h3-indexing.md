## Overview

H3 is Uber's hexagonal hierarchical spatial indexing system that converts geometries and coordinates into discrete integer cell IDs at configurable resolutions. The key insight is that spatial joins become integer equality joins — a neighborhood containment check turns into a SQL `WHERE h3_index IN (...)`, which runs on any standard database without a spatial extension. Hexagons are preferred over squares because all six neighbors are equidistant from the center, making them better for modeling movement, demand, and coverage.

## Key Concepts

### 1. What H3 Is

H3 maps any (lat, lon) point to a unique 64-bit integer representing a hexagonal cell at a chosen resolution. Polygons map to a set of cell IDs that cover them. Because the IDs are integers, spatial operations reduce to set operations — membership, intersection, and k-ring neighbor expansion are all integer arithmetic.

### 2. H3 Resolution Levels

H3 has 16 resolution levels (0–15). Resolution 0 cells are continent-sized; resolution 15 cells are roughly one square meter. The hierarchy is strict: each cell at resolution `r` is fully contained within exactly one cell at resolution `r-1`, enabling compaction — a contiguous zone can be expressed as a smaller set of mixed-resolution IDs that perfectly cover the same area with less data.

### 3. Spatial Joins as Integer Joins

The practical payoff of H3 is performance. Converting driver positions and neighborhood polygons to H3 indices at the same resolution turns a geometric point-in-polygon test into a `GROUP BY h3_index` or `isin()` check. These operations run on standard query engines and dataframe libraries (DuckDB, BigQuery, Pandas) without GEOS, JTS, or PostGIS.

## 1. What is Uber H3?

H3 is a hexagonal hierarchical indexing system. Instead of storing a polygon as
a list of coordinates, you can represent it as a set of unique bit integers
(Hexagon IDs).

- **Hexagons**: Unlike squares, hexagons have the same distance between their
  center and all neighbors. This is critical for modeling movement (e.g., driver
  demand).
- **Hierarchy**: One large hexagon can be subdivided into smaller hexagons,
  allowing for different resolutions in the same system.

## 2. Spatial Joins without Geometry

The magic of H3 is that a "Spatial Join" becomes a **Standard Integer Join**. If
you want to know which delivery drivers are in a specific neighborhood:

1. Map every driver's Lat/Lon to an H3 index.
2. Map the neighborhood polygon to a list of H3 indices.
3. Run a SQL `JOIN` on the H3 index columns.

## 3. Why This Matters for Product Patterns

- **Speed**: H3 operations are thousands of times faster than geometric joins.
- **Privacy**: Aggregating raw GPS points into H3 cells is a common pattern for
  anonymizing user location data while keeping it useful for analysis.
- **Scalability**: It allows you to run complex spatial logic on standard
  databases that don't even have a "Spatial" extension.

## 4. The H3 Catch: Trade-offs & Limitations

While powerful, H3 is not a "silver bullet" for every spatial problem.

1. **Precision Loss (Quantization)**: When you map a point to an H3 index, you
   lose its exact location. The point effectively "snaps" to the center of the
   hexagon. For high-precision mapping (like surveying), H3 is an aggregation
   tool, not a storage format for raw points.
2. **The "Pentagon Problem"**: To cover a sphere with hexagons, you
   mathematically _must_ include 12 pentagons. While H3 handles this gracefully,
   topology operations near these 12 points can have slight irregularities.
3. **Area Distortion**: Hexagons near the poles have slightly different areas
   than those at the equator (though much less distortion than square grids like
   Mercator).
4. **Raster Incompatibility**: Most satellite data is square-tiled. Converting
   raster data to H3 often involves expensive re-sampling.

## Practical Exercises

You'll aggregate a simulated high-frequency event stream (ride-share pickups) into H3 hexagons to build a demand heatmap, then compute a k-ring catchment zone around a location and compact it into a minimal set of mixed-resolution cell IDs — all without writing a single geometric predicate.



