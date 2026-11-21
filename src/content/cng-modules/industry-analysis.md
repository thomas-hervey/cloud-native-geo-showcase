> Status: Reference / Orientation Module — no exercises. Read to understand the
> commercial ecosystem and capabilities of leading geospatial AI platforms.

## Overview

The geospatial industry is consolidating around cloud-native formats and AI-augmented workflows, with traditional GIS vendors adapting alongside cloud-native startups. This module surveys the platform landscape — from foundation model providers and EO satellite constellations to serverless spatial analytics and open data consortia — along with the competitive dynamics shaping how geospatial data is produced, processed, and consumed. Understanding what leading platforms solve out-of-the-box informs architectural decisions about when to build versus buy.

## Key Concepts

### 1. The Platform Landscape

The modern geospatial platform landscape spans distinct capability layers: EO data providers (Planet, ICEYE, Pixxel, BlackSky) supply the raw imagery; foundation model developers (Google DeepMind, IBM/NASA, Allen Institute) provide pretrained models; analytics platforms (CARTO, Wherobots, DuckDB Spatial) handle scalable spatial computation; and map/data platforms (Mapbox, Overture, Foursquare) supply the base layers and POI data that ground applications. Each layer is rapidly converging on cloud-native formats — COG, GeoParquet, STAC — as the interoperability substrate.

### 2. AI Augmentation Across the Stack

Every major platform is embedding AI at multiple levels: conversational NL-to-SQL (Felt, Mapbox MapGPT), agentic workflow orchestration (CARTO's MCP-powered agents, Google's Geospatial Reasoning Agent), automated feature extraction (Esri's deep learning tools, Felt's browser-based object detection), and foundation model integration (CARTO + AlphaEarth, Microsoft Planetary Computer + Pangeo). The platforms that win are those that abstract the frontier problems — CRS heterogeneity, hallucinated geographies, spatial semantic similarity — so developers can focus on application logic.

### 3. Build vs. Buy Decision Framework

The right architectural choice depends on what your product requires: agentic spatial database analysis favors CARTO or Google's Geospatial Reasoning Agent; conversational routing and POI search favors Mapbox MapGPT; rapid EO feature extraction favors Esri or Felt's digitization pipelines; serverless analytics at scale favors DuckDB Spatial or Wherobots SedonaDB; 3D digital twin infrastructure favors Bentley + Cesium. Open data layers (Overture Maps, Foursquare OS Places) reduce the cost of bootstrapping a new geospatial application's base map and POI coverage.

As you build cloud-native geospatial systems, it's critical to understand what
the commercial ecosystem provides out-of-the-box. Many of the architectural
hurdles discussed in (like NL-to-SQL, embedding-based retrieval, and
handling spatial APIs) are being actively solved—or abstracted away—by leading
platforms.

The geospatial industry is a large and fast-growing market. The traditional GIS analyst sitting behind ArcGIS Pro
is being supplemented—and in some workflows, replaced—by natural-language-driven
autonomous pipelines, serverless analytics on cloud-optimized formats, and AI
copilots embedded in every major platform.


## Executive Summary: The GeoAI Landscape

| Company / Platform               | Core Product Features & AI Capabilities                                                                             | Frontier Problems Addressed                          |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| **Google Earth AI**              | AlphaEarth foundation model, Geospatial Reasoning Agent (Gemini-powered), Population Dynamics models                | LLM Spatial Reasoning, Evaluation Benchmarks, Temporal Semantics |
| **CARTO**                        | "The Agentic GIS Platform", MCP workflows, AlphaEarth integration, data-never-leaves architecture                   | Agentic GIS, MAUP (via H3/spatial indexing), Privacy             |
| **Felt**                         | NL-to-SQL web GIS, generative map UI, browser-based object detection & vector digitization                          | Geospatial Semantic Similarity                                   |
| **Esri (ArcGIS GeoAI)**          | Azure OpenAI integration, ArcGIS for Teams Copilot, deep learning feature extraction, Overture data in Living Atlas | 3D/Multimodal Spatial AI, Qualitative Spatial Reasoning          |
| **Mapbox**                       | MapGPT (conversational location AI), MCP Server for AI agents, autonomous routing, generative vector tile styling   | Hallucinated Geographies (Routing and POIs)                      |
| **Planet Labs**                  | Pelican constellation (40cm + on-orbit AI), Planetary Variables, satellite-as-a-service model                       | Temporal Geospatial Semantics, Ground Truth                      |
| **ICEYE**                        | World's largest SAR constellation, 16cm resolution, major defense contracts                                          | Remote Sensing, Surveillance/Ethics                              |
| **Pixxel**                       | Highest-res commercial hyperspectral (5m, 150+ bands), NRO contract, NASA CSDA program                              | Ground Truth, Foundation Model Data                              |
| **BlackSky / Vantor**            | BlackSky Gen-3 (35cm + AI analytics, sub-hourly delivery); Vantor's Tensorglobe 3D fusion platform                  | Temporal Semantics, 3D/Multimodal                                |
| **Wherobots**                    | SedonaDB (open-source spatial analytical DB), RasterFlow (planetary-scale inference on Iceberg)                     | Standards Adherence, Cloud-Native Formats                        |
| **NVIDIA**                       | Omniverse Smart City Blueprint, Earth-2 digital twin, cBottle climate AI, FourCastNet                               | 3D Digital Twins, Foundation Models                              |
| **Bentley + Cesium**             | CesiumJS open 3D platform + iTwin digital twins, 3D Tiles in game engines, Gaussian splats                          | 3D/Multimodal Spatial AI                                         |
| **DuckDB Spatial**               | Dedicated SPATIAL_JOIN operator, serverless spatial analytics, GeoParquet native support                            | Standards Adherence, Cloud-Native Formats                        |
| **Microsoft Planetary Computer** | Global STAC API, scalable Pangeo environments, AI for Earth conservation                                            | CRS Heterogeneity, Standards Adherence (STAC)                    |
| **Overture Maps Foundation**     | 28+ members incl. Esri, GERS entity IDs, monthly releases across 6 themes, Esri contributing data back              | Vagueness/Uncertainty, Geospatial Semantic Similarity            |
| **Foursquare**                   | FSQ OS Places (100M+ global POIs, Apache 2.0, monthly updates)                                                      | Open Data, Geospatial Semantic Similarity                        |
| **Element 84 & Dev Seed**        | Cloud-native STAC catalogs, Zarr data streaming, EO LLM ingestion pipelines                                         | Standards Adherence (Zarr/COG), Temporal Geospatial              |


## Summary: Building vs. Buying

When architecting a new geospatial application, map your requirements against
this landscape:

1. **Do I need an agent to analyze my private spatial database?** → CARTO's MCP
   workflows or Google's Geospatial Reasoning Agent.
2. **Do I need conversational routing and POI search?** → Mapbox MapGPT + MCP
   Server.
3. **Do I need to rapidly extract features from imagery?** → Esri or Felt's
   automated digitization pipelines, or fine-tune a GeoFM (Prithvi, Clay).
4. **Do I need daily temporal change-detection metrics?** → Planet's Planetary
   Variables.
5. **Do I need serverless spatial analytics at scale?** → DuckDB Spatial +
   GeoParquet, or Wherobots SedonaDB for larger workloads.
6. **Do I need 3D digital twin infrastructure?** → Bentley + Cesium for
   visualization, NVIDIA Omniverse for simulation.
7. **Do I need a custom EO pipeline?** → STAC/Zarr patterns from Element 84,
   Microsoft Planetary Computer, and Development Seed.
8. **Do I need an open basemap layer?** → Overture Maps + Foursquare OS Places.

