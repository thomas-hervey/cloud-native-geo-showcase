## Overview

Geospatial foundation models — large vision transformers pretrained on satellite and aerial imagery — enable transfer learning for earth observation tasks without training from scratch. Models like Prithvi, SatMAE, and Clay embed spatial and temporal context that general-purpose vision models lack, because they are trained on multispectral bands, temporal image sequences, and geospatial coordinates rather than natural photographs. This shifts the paradigm from bespoke per-task model training to a fine-tune-or-prompt workflow grounded in planetary-scale pretraining.

## Key Concepts

### 1. What Makes an EO Foundation Model Different

Earth observation foundation models differ from general vision models in three key ways: they accept multispectral input beyond RGB (NIR, SWIR, SAR), they are trained on temporal sequences of imagery to capture change over time, and they encode geospatial coordinates as part of the model's context. These properties let them represent dynamic processes — flooding, fire scars, crop phenology — that a model trained on static natural photographs simply cannot learn.

### 2. Fine-Tuning vs. Zero-Shot on EO Tasks

Like LLMs, EO foundation models can be used in zero-shot mode (prompt with a bounding box or point, extract a feature) or fine-tuned on labeled data for higher accuracy on a specific task. SAM and SAM-Geo demonstrate zero-shot segmentation: no training required, just a spatial prompt. Prithvi and SatLas are designed for fine-tuning with minimal labeled examples, making them practical for organizations that have some annotated ground truth but not enough to train from scratch.

### 3. Key Models and Their Training Data

The leading EO foundation models differ significantly in their pretraining corpus: Prithvi (IBM/NASA, actively versioned since the original HLS-trained release) is trained on Harmonized Landsat Sentinel data with temporal depth; SatLas (Allen Institute) is trained on Sentinel-2 for multi-task generalization across geographies; AlphaEarth (Google DeepMind) synthesizes heterogeneous EO data into dense per-patch embeddings for a range of downstream tasks. The choice of pretraining data directly determines where a model generalizes well and where it fails — a model trained on temperate mid-latitude imagery will underperform on polar or tropical scenes.

## The Shift to Foundation Models

In recent years, the geospatial industry has moved from training bespoke models
for every meaningful task (e.g., "detect corn in Iowa", "find solar panels in
Germany") to using **Foundation Models**.

These are large-scale models trained on vast amounts of unlabeled satellite
imagery using self-supervised learning. Just as LLMs (like GPT-4) understand
language structure, GFMs understand the visual structure of the Earth—textures,
shapes, and spectral relationships—without needing explicit labels.

## Leading Examples

### 1. AlphaEarth (Google DeepMind)

**Purpose:** A "virtual satellite" that synthesizes heterogeneous Earth
observation data into a dense, continuous embedding field. **Key Innovation:**
Instead of just classifying pixels, AlphaEarth creates a dimensional embedding
for every 10x10m patch of Earth. These embeddings are "dense representations" of
the landscape that can be used for any downstream task (classification, change
detection, generative reconstruction) with very little labeled data. **Impact:**
It effectively allows users to query the physical state of the planet
mathematically, enabling applications like "show me all areas that look like
this damaged infrastructure" across the entire globe instantly.

### 2. Segment Anything Model (SAM) & SAM-Geo (Meta/Open Source)

**Purpose:** Zero-shot image segmentation. **Key Innovation:** SAM does not know
_what_ a building is, but it knows where an object begins and ends. When applied
to satellite imagery (SAM-Geo), it can instantly extract millions of building
footprints, roads, and fields without any model training—just prompting.

### 3. Prithvi (IBM/NASA)

**Purpose:** A temporal vision transformer trained on HLS (Harmonized Landsat
Sentinel) data. **Key Innovation:** Unlike static image models, Prithvi
understands _time_. It is designed to model dynamic processes like flooding,
fire scars, and crop phenology, making it powerful for climate monitoring.

### 4. SatLas (Allen Institute for AI)

**Purpose:** A multi-task foundation model for global satellite imagery
analysis. **Key Innovation:** Trained on Sentinel-2, it generalizes well across
diverse geographies and seasons for tasks like renewable energy mapping and tree
cover analysis.

## Why This Matters for Product Patterns

The integration of GFMs into modern data pipelines has created a repeatable
"Foundation Why This Matters for Product Patterns" for building geospatial
applications:

1. **Semantic Search (Embeddings):** Instead of searching for metadata (e.g.,
   "images with < 10% cloud cover"), we convert imagery into **vector
   embeddings** using models like AlphaEarth or SkyCLIP. This allows us to
   search by concept (e.g., "find me images that look like this shipping
   container depot").

2. **Zero-Shot Extraction (Vision):** Once relevant imagery is found, we run a
   GFM (like SAM) to extract features. We don't train a model; we just prompt
   the foundation model with a bounding box or point.
   - _Tooling:_ rasterio -> numpy -> SAM Inference -> GeoParquet.

3. **Analysis & Enrichment:** The extracted polygons form a "Digital Twin." We
   then overlay other datasets (demographics, risk layers) to generate insights.

## Future Trends & Challenges

- **Multimodal GFMs:** Models that combine text, imagery, and vector data (e.g.,
  "Show me all damaged bridges reported in the last week").
- **On-Device Inference:** Running quantized versions of models like SAM
  directly on satellites or drones to reduce bandwidth.
- **Hallucination:** Like LLMs, vision models can "hallucinate" features that
  aren't there. Validation against ground truth (like OpenStreetMap or
  authoritative government data) remains critical.
