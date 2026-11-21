## Overview

Machine learning applied to geospatial data spans a wide range of approaches — from classical spatial statistics and unsupervised clustering to deep learning for satellite imagery classification and point cloud segmentation. The core challenge is matching the right ML method to geospatial data's unique characteristics: irregular grids, spatial autocorrelation, projection-sensitivity, and multiscale structure. Understanding this fit is a foundational skill for geospatial product engineering.

## Key Concepts

### 1. Classical Spatial ML

Geospatial datasets exhibit spatial autocorrelation — nearby observations tend to be similar — which violates the independence assumption underlying most standard ML algorithms. Classical approaches like spatial regression, kriging, and clustering (K-Means over spectral bands) account for this structure explicitly. Unsupervised clustering is often the right starting point when labeled training data is unavailable, as with raw satellite imagery.

### 2. Deep Learning for Imagery

Convolutional neural networks excel at learning spatial hierarchies in raster data — detecting edges, textures, and shapes at multiple scales. Applied to satellite imagery, CNNs power tasks like land-cover classification, change detection, and object detection (building footprints, roads, solar panels). The key engineering challenge is handling the scale of imagery data efficiently, which is why cloud-native formats like COGs and tools like rioxarray matter.

### 3. Fitting ML to Geospatial Data Characteristics

Geospatial data is not interchangeable with tabular or image data. Irregular grids, projection distortions, spectral band relationships (NDVI, NDWI), and tile-scale sampling all affect model performance. Choosing the right feature representation — raw bands, derived indices, embeddings — and the right spatial post-processing (sieve filters, vectorization) determines whether an ML pipeline produces cartographically coherent outputs or noisy artifacts.

This module transitions from "accessing data" to "creating information." We will
move beyond simple visualization and build a pipeline that extracts land-cover
insights from raw spectral bands.

## 1. The Imagery-to-Information Pipeline

A modern geospatial ML pipeline involves several discrete stages:

1. **Remote Chipping**: Pulling specific "chips" (small AOIs) from massive
   cloud-hosted COGs without downloading the whole file.
2. **Feature Augmentation**: Calculating spectral indices (like NDVI) to help
   the model distinguish between surfaces (like vegetation vs. water).
3. **Modeling**: Applying algorithms (like K-Means) to group pixels into
   thematic clusters.
4. **Spatial Post-processing**: Cleaning up "noise" in the classification
   output.
5. **Vectorization**: Turning the pixel-based results into high-performance
   vector formats (**GeoParquet**).

## 2. Feature Augmentation (NDVI & NDWI)

Raw RGB bands are often not enough for robust classification. We derive indices
to highlight specific characteristics:

- **NDVI (Normalized Difference Vegetation Index)**: Uses Red and NIR bands to
  highlight greenery.
- **NDWI (Normalized Difference Water Index)**: Uses Green and NIR bands to
  highlight water bodies.

Adding these as "feature bands" makes it significantly easier for a model to
separate land-cover types.

## 3. Spatial Post-processing (Sieving)

ML models often produce "salt-and-pepper" noise—isolated pixels that are
technically classified but don't represent a coherent feature. We use a **Sieve
Filter** to remove these small patches and merge them with their largest
neighbors, resulting in a map that looks more like a human-drawn cartographic
product.


## Practical Exercises

Run a complete land-cover classification pipeline — from Sentinel-2 data search through GeoParquet export — using spectral indices, K-Means clustering, and sieve filtering.



## 4. Why GeoParquet + DuckDB?

This combination is the current "gold standard" for cloud-native vector
analytics:

- **GeoParquet**: The storage format that allows us to treat vector data like a
  database table.
- **DuckDB**: The engine that can query that data directly without a traditional
  GIS server.

By calculating the total area of each cluster (Water, Forest, Urban) in a single
SQL query, we complete the journey from **Raw Pixels** to **Actionable Policy
Insights**.

## 5. A Note on Accuracy: Why Foundation Models?

> [!IMPORTANT]
> You might notice that K-Means (unsupervised learning) struggles to perfectly
> distinguish between buildings, roads, and shadows in complex urban scenes.
>
> **Why?** Unsupervised models only see statistical patterns in pixel values.
> They don't "understand" shapes or context (like "this rectangle is a
> building").
>
> In production, we typically move beyond this using:
>
> 1. **Supervised Learning**: Training models on millions of hand-labeled
>    examples (like the Dynamic World dataset).
> 2. **Foundation Models (Prithvi, Clay)**: Large-scale models that have
>    "learned" the earth's features, allowing for much higher accuracy with
>    minimal effort.
