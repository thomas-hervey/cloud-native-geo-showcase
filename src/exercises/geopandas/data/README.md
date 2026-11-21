# Module 34 Exercise Data

This directory contains NYC open data used throughout the GeoPandas Fundamentals exercises.

## Included in Git

| File | Size | Description |
|---|---|---|
| `custom_nyc_neighborhoods.geojson` | ~1.4MB | NYC neighborhood boundaries (Pedia Cities) |
| `custom_pedia_cities_nyc.geojson` | ~1.4MB | Alternative neighborhood classification |
| `neighborhood_access_index.geojson` | ~1.8MB | Walkability/transit access scores by neighborhood (NYU Furman Center) |
| `New York City Bike Routes_20241223.geojson` | ~17MB | All bike lanes and routes |
| `Parks Properties_20241223.geojson` | ~7.4MB | Park polygon boundaries |
| `nyc_subway_entrances/` | shapefile | NYC subway entrance point features |
| `SchoolPoints_APS_2024_08_28 (1)/` | shapefile | NYC public school locations |
| `SchoolPoints_APS_2024_08_28 (1).zip` | ~116KB | Zipped school points shapefile |
| `nyu_2451_34208.zip` | ~66KB | NYU spatial data archive |

## Not Included in Git (Large Files)

These files are gitignored due to size. They are available locally if you cloned the original geopandas-tutorials repo:

| File | Size | Description |
|---|---|---|
| `es_cn.parquet` | ~131MB | Elementary school + US Census demographic data |
| `internet-speeds.parquet` | ~33MB | Internet speed measurements with geolocation |

### To Download (if needed)

```bash
# es_cn.parquet — from the NYU Furman Center or original repo
# internet-speeds.parquet — from the original repo source

# Place files in this directory before running notebooks that reference them
```
