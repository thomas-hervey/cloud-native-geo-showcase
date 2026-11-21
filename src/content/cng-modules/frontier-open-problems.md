> Status: Reference / Orientation Module — no exercises. Read after completing
> the elective modules. Revisit every 6-12 months as the field evolves.

## Overview

This capstone module surveys open problems at the frontier of geospatial AI and cloud-native geo — from topology and spatial reasoning limits in LLMs to the evaluation benchmark gap, real-time streaming challenges, and foundation model deployment for earth observation. Each section names the unsolved problem, explains why it's hard, and maps it to a product or research horizon. For a product manager, this is a map of where the interesting bets are being made and which are likely to pay off in 1-2 years versus 5-10.

## Key Concepts

### 1. Knowledge Representation Limits

LLMs process space linguistically rather than geometrically — they have no internal coordinate system, no topology engine, and no awareness of projection distortions. This produces cascading failures: hallucinated place names, wrong coordinates, category confusion, and systematic errors on spatial predicate tasks (disjoint vs. overlaps, distance estimation, landmark-route-survey reasoning). Emerging benchmarks (GPSBench, GeoGramBench) are beginning to quantify these limits, but the fundamental architectural gap between linguistic and geometric reasoning remains unsolved.

### 2. Foundation Model Deployment Gaps

EO foundation models (Prithvi, SatLas, AlphaEarth) have demonstrated strong research results but face significant production deployment challenges: ground truth data is geographically biased toward temperate mid-latitude areas, fine-tuning requires validation pipelines, and training costs raise equity concerns about who controls planetary-scale spatial intelligence. Evaluation benchmarks (GEO-Bench, PANGAEA) exist but have not yet produced a community-consensus standard analogous to ImageNet for vision.

### 3. Infrastructure and Data Gaps

Cloud-native formats (COG, GeoParquet, PMTiles) have won the community's adoption, but real-time streaming at scale, standardized benchmark datasets for spatial NL-to-SQL, and probabilistic spatial databases for vague geography remain open engineering problems. OGC standards move slowly relative to de facto adoption (GeoParquet was ubiquitous before its OGC process completed), and AI agent communication protocols (MCP, A2A) may shift interoperability from the data format level to the workflow level entirely.

the elective modules taught you how to build a working geospatial AI system and
extend it toward larger scale. But every architectural choice you made was a
workaround for a deeper, unsolved problem. This module names those problems,
explains why they're hard, and tells you where to follow the research.

For a PM, this is a map of where the interesting product bets are being made —
and, equally important, which bets are likely to pay off in 1-2 years vs. which
are 5-10 year research horizons.

### Table of Contents

| #  | Topic                                                                                                          | Core Challenge                                   |
| -- | -------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| 1  | [Standards Adherence Gap](#1-the-standards-adherence-gap)                                                      | Specs exist but adoption lags                    |
| 3  | [Agentic GIS](#3-agentic-gis--autonomous-spatial-analysis)                                                     | Autonomy levels, reliability, discovery          |
| 4  | [Ground Truth & Data Quality](#4-ground-truth--the-data-quality-bottleneck)                                    | Training data gaps and geographic bias           |
| 5  | [Semantic Similarity](#5-the-geospatial-semantic-similarity-problem)                                           | Vector embeddings can't encode spatial relations |
| 6  | [GeoSPARQL & Graph Explosion](#6-geosparql-and-graph-explosion)                                                | Linked data at planetary scale                   |
| 7  | [Hallucinated Geographies & LLM Spatial Reasoning](#7-hallucinated-geographies--the-llm-spatial-reasoning-gap) | LLMs fail basic spatial tasks                    |
| 8  | [CRS Heterogeneity](#8-coordinate-reference-system-heterogeneity)                                              | Silent projection mismatches                     |
| 9  | [Temporal Semantics](#9-temporal-geospatial-semantics)                                                         | Time-varying geometries                          |
| 10 | [Vagueness & Uncertainty](#vagueness-uncertainty-and-imprecise-geographies)                                    | Fuzzy boundaries, UQ for spatial AI              |
| 11 | [Qualitative Spatial Reasoning](#qualitative-spatial-reasoning-qsr-and-topological-logic)                      | Topological logic for AI                         |
| 12 | [MAUP & Scaling](#the-modifiable-areal-unit-problem-maup-and-scaling)                                          | Aggregation changes conclusions                  |
| 13 | [Privacy, Ethics & Governance](#privacy-ethics-and-governance)                                                 | Surveillance vs. utility                         |
| 14 | [3D & Multimodal Spatial AI](#14-3d-point-clouds-and-multimodal-spatial-ai)                                    | Digital twins, indoor/outdoor fusion             |
| 15 | [Evaluation Benchmarks](#the-evaluation-benchmark-gap)                                                         | No standard way to measure spatial AI            |
| 16 | [Where to Follow Research](#where-to-follow-the-research)                                                      | Venues, labs, and feeds                          |
| 17 | [PM Perspective](#pm-perspective-which-bets-are-worth-making)                                                  | Which bets pay off when                          |

## 1. The Standards Adherence Gap

### What exists

The Open Geospatial Consortium (OGC) has done serious work:

| Standard                 | What it does                                                             | Status                                            |
| ------------------------ | ------------------------------------------------------------------------ | ------------------------------------------------- |
| **GeoSPARQL 1.1** (2022) | SPARQL extension for topological spatial queries in RDF knowledge graphs | Spec complete; implementations sparse             |
| **OGC API suite**        | REST/JSON replacements for WMS/WFS/WCS                                   | Actively deployed by USGS, Copernicus, others     |
| **GeoDCAT-AP**           | DCAT metadata profile for geospatial datasets, maps to STAC concepts     | Adopted in EU; rare elsewhere                     |
| **STAC**                 | Spatiotemporal Asset Catalog — you've been using this                    | Widely adopted in cloud-native community          |
| **GeoParquet**           | Column metadata standard for geometry in Parquet files                   | Rapidly adopted; DuckDB spatial reads it natively |

### Why adoption lags

Standards bodies move slowly. GeoSPARQL 1.0 was published in 2012; meaningful
LLM-compatible implementations barely exist in 2025. The causes are structural:

- **Volunteer committee dynamics**: OGC working groups are composed of company
  representatives who balance standards work against product deadlines.
- **Interoperability testing takes years**: Certifying that two implementations
  behave identically requires expensive test suites and coordination.
- **Legacy install bases**: A government GIS shop running ArcGIS 10.x on-prem
  will not adopt OGC API — Features this year, regardless of spec quality.
- **AI systems don't (yet) consume standards natively**: An LLM generating SQL
  has no built-in awareness of GeoSPARQL or OGC API endpoints. Bridging these
  requires explicit tooling that nobody has standardized.

### PM implication

You cannot assume that a dataset you want to query has a standardized interface.
Building a geospatial product that depends on OGC API adoption is a product bet
on enterprise GIS modernization timelines — typically 5-10 years. STAC is the
exception: it won the cloud-native data community's adoption fast enough that
you can safely depend on it today.

> The frontier report documents how the Cloud-Native Geospatial community's
> "move fast" approach — setting de facto standards through adoption — is
> creating a two-speed ecosystem with OGC's formal process. GeoParquet became
> ubiquitous before its OGC process completed. PMTiles has no OGC track at all.
> Meanwhile, AI agent communication protocols (Anthropic's MCP and Google's A2A)
> may shift interoperability from the data format level to the workflow level
> entirely.

## 3. Agentic GIS & Autonomous Spatial Analysis

### What's happening

The integration of LLMs with GIS tools has moved beyond chatbots to what the
industry calls "agentic GIS" — AI systems that autonomously plan, discover data,
execute spatial analyses, and interpret results.

Penn State's Autonomous GIS lab (Zhenlong Li, Huan Ning) proposes a framework
with **five core autonomous goals**: self-generating, self-executing,
self-verifying, self-organizing, and self-growing. Drawing from autonomous
vehicle conventions, they define **five levels of GIS autonomy**:

1. **Level 1 — Routine-aware GIS**: Automates predefined processes
2. **Level 2 — Workflow-aware GIS**: Generates and executes workflows based on
   user input
3. **Level 3 — Data-aware GIS**: Autonomously identifies, retrieves, and
   prepares appropriate datasets
4. **Level 4 — Result-aware GIS**: Evaluates its outputs and iteratively refines
   its approach
5. **Level 5 — Knowledge-aware GIS**: Fully autonomous, learning from past
   experience to improve future performance

Current systems operate at roughly Level 2–3 (task-level automation with human
oversight).

Key implementations:

- **CARTO** now brands itself "The Agentic GIS Platform" with MCP-powered AI
  Agents
- **Google's Geospatial Reasoning Agent** (Gemini-powered) decomposes complex
  queries into multi-step plans calling Earth Engine, BigQuery, and foundation
  models
- **Penn State's GIS Copilot** demonstrates multi-step task automation in QGIS
- **Mapbox** released an MCP Server for AI agent spatial reasoning

### The open problems

- **Scalability**: Handling 30,000+ Census variables or 200,000+ OGC services
  without overwhelming LLM context
- **Reliability**: 14% failure on advanced tasks is unacceptable for disaster
  response
- **Data discovery**: Autonomously finding and evaluating relevant datasets from
  the open web remains unsolved
- **Tool interoperability**: MCP and A2A protocols are the most promising
  approaches, but standardization is early

### PM implication

Reliable autonomous GIS for routine analysis is likely a near-term (2–3 year)
prospect; complex multi-step spatial analysis that requires no human oversight
is a longer-term research horizon. The market implication: product value shifts
from "doing the analysis" to "orchestrating the workflow" and "validating the
results."

---

## 4. Ground Truth & the Data Quality Bottleneck

Foundation models reduce the need for labeled data through self-supervised
pre-training, but fine-tuning still requires ground truth. The problem:

- Key datasets (SpaceNet, BigEarthNet v2.0, xBD) cover limited geographies and
  land cover types
- **Most GeoFMs are trained predominantly on temperate, mid-latitude land
  areas** — polar regions, open oceans, and tropical forests are
  underrepresented
- For novel tasks and underrepresented geographies, ground truth collection
  remains expensive and slow

Weak supervision and self-supervised approaches are gaining traction: TerraMind
generates missing modalities as intermediate reasoning steps; AlphaEarth
embeddings enable downstream classification with minimal labeled data. But these
don't eliminate the need for validation data.

### PM implication

If your product operates outside temperate mid-latitude land (which includes
much of the developing world, oceans, and polar regions), do not assume
foundation models will work out of the box. Budget for local ground truth
collection and validation.

---

## 5. The Geospatial Semantic Similarity Problem

### What vector embeddings actually measure

When you embed text into a vector space, similar meanings end up close together.
"coffee shop" and "café" land near each other. This is useful for schema RAG :
embed your dataset descriptions, retrieve the ones semantically closest to the
user's query.

But spatial relationships are not semantic. Consider:

- "near" (distance predicate — requires coordinate math)
- "within" (containment predicate — requires geometry intersection)
- "adjacent to" (topological predicate — requires shared boundary check)
- "visible from" (viewshed predicate — requires DEM + line-of-sight calculation)

None of these map cleanly to vector similarity. An embedding of "the park near
the school" does not encode that "near" means within 500 meters. The model
understands the words but not the spatial relationship they imply.

### Active research

| Project                           | Approach                                                                                                                         | Status                                           |
| --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| **GeoBERT** (2021)                | Pre-train BERT on geospatial text corpora (Wikipedia geo articles, OSM tags) to improve geographic NER and place-name embeddings | Published; not widely deployed                   |
| **SpaBERT** (2022)                | Encode spatial relationships (distance, direction) as additional features alongside text embeddings                              | Research paper; no production library            |
| **Geographic knowledge graphs**   | Wikidata, GeoNames, Linked Geo Data — encode places as graph nodes with typed spatial edges                                      | Exists but see Section 6 for the scaling problem |
| **GeoLLM / SpatialLM** (2024)     | Fine-tune LLMs on spatial reasoning tasks; teach models to use ST_* functions correctly                                          | Early papers; not yet production-grade           |
| **Overture's schema embeddings**  | Overture Maps consortium is exploring embedding their taxonomy for semantic search across the global dataset                     | Active R&D; no public release                    |
| **Spatial-RAG** (Yu et al., 2025) | Gives LLMs access to external spatial knowledge through geodesic distance graphs and spatial SQL databases                       | Research prototype; promising direction          |

### What's missing

A **geospatial embedding model** that natively understands both semantic
similarity ("coffee shop" ≈ "café") and spatial predicates ("within 500m of a
park") — and can combine them in a single retrieval step — does not exist as a
widely deployable tool. Every production system today either:

- Uses text embeddings and delegates spatial filtering to SQL (Scout's
  approach), or
- Uses spatial databases and delegates semantic matching to keyword search.

The hybrid that does both well simultaneously is an open research problem.

### PM implication

When a user says "coffee shops with a cozy vibe near a park", you currently need
two systems: an LLM to parse "cozy vibe" (semantic), and DuckDB/PostGIS to
evaluate "near a park" (spatial). This two-step architecture is a product
limitation disguised as a design choice. The product that collapses this into a
single embedding-and-retrieval step will have a meaningful UX advantage.

---

## 6. GeoSPARQL and Graph Explosion

### What GeoSPARQL is

GeoSPARQL is an OGC standard for querying RDF (Resource Description Framework)
knowledge graphs that contain spatial features. It adds vocabulary for geometry
literals, coordinate reference systems, and topological functions (sfContains,
sfWithin, sfIntersects, etc.).

Government agencies and research institutions store data as Linked Open Data
(LOD) — RDF triples in systems like Fuseki or GraphDB. The UK Ordnance Survey,
US Census TIGER/Line, and DBpedia all expose spatial data this way. GeoSPARQL is
the standard query language for this data.

### Why graph explosion happens

A SPARQL query traverses a graph. Each hop multiplies the candidate set. Add a
spatial predicate — "find all features sfWithin this polygon" — and you now need
to evaluate geometry intersection for every candidate at every hop. For a simple
two-hop query over a city's LOD dataset (e.g., `?building :locatedIn ?block` then `?block :sfWithin :downtown_polygon`), the engine must:

1. Find all triples with `:locatedIn` predicate (potentially millions)
2. For each, check if the subject's geometry is within the target polygon
3. Filter by the `?block` binding

Without careful spatial indexing (R-trees, H3 pre-computation), this is O(n²) or
worse. Most triple stores had weak spatial indexing until recently. GeoSPARQL
1.1 adds metadata for spatial reference systems and encourages better index
hints, but the fundamental join problem remains.

### Why this matters for AI systems

If you try to build a geospatial RAG system over LOD/RDF data instead of
GeoParquet, you encounter this problem immediately. An LLM generating SPARQL
with spatial predicates will regularly produce queries that time out or return
nothing — not because the logic is wrong, but because the query planner doesn't
have enough spatial context to execute efficiently.

Research groups (including at Karlsruhe Institute of Technology and the
University of Jyvaskyla) are working on SPARQL query planners that incorporate
spatial statistics, but it remains an active problem rather than a solved one.

### PM implication

If your data lives in a government LOD endpoint (and in the US, EU, and UK, a
lot of public sector spatial data does), building an NL interface on top of it
is significantly harder than building on GeoParquet. Budget for longer query
times, stricter query validation, and a fallback to pre-computed spatial joins.

---

## 7. Hallucinated Geographies & the LLM Spatial Reasoning Gap

### The problem

LLMs hallucinate. In most domains, this means confident-sounding but wrong
facts. In the geospatial domain, it means:

- **Invented place names**: "Dolores Street Coffee" does not exist, but the
  model generates it confidently.
- **Wrong coordinates**: The model claims Dolores Park is at (-122.4800,
  37.7590) when the real centroid is (-122.4271, 37.7596).
- **Non-existent streets**: "The intersection of Valencia and Guerrero" — these
  streets are parallel and don't intersect.
- **Category confusion**: A query for "breweries" returns results for
  "brewpubs", "taprooms", and "wine bars" because the model doesn't know the
  Overture taxonomy.

### The deeper problem: spatial reasoning is fundamentally broken in LLMs

Hallucinated geographies are a symptom of a more fundamental issue — **LLMs
process space linguistically, not geometrically**. A systematic body of evidence
from 2024–2026 establishes cascading failures:

- **GPSBench**: Covers a broad range of spatial task types and shows consistent
  weakness in landmark-route-survey cognitive reasoning
- **GeoGramBench**: Even frontier models struggle at the highest levels of
  procedural geometry abstraction
- **SURPRISE3D**: Multimodal models that perform well in zero-shot tests have
  shown near-zero accuracy on 3D spatial reasoning tasks
- **Geographic bias**: Models show meaningfully higher error rates for
  underrepresented geographies (Sub-Saharan Africa, polar regions) relative to
  North America and Western Europe, reflecting training data imbalance

Models also confuse spatial predicates — mislabeling "disjoint" as "overlaps"
and reversing directions in ways that humans rarely get wrong (IJGIS 2025).

### Why it's hard to catch

The standard NL-to-SQL approach (the elective modules) avoids some of these: by
constraining the LLM to generate SQL over a known schema with a closed
vocabulary, you eliminate most category hallucinations. The model can't
hallucinate a category that isn't in the prompt.

But geometry hallucination is harder. If the user asks "is Dolores Park near the
Mission?" and the LLM reasons about this from training data rather than
executing a spatial query, it may give a correct-sounding answer based on
hallucinated coordinates. The current fix is to always route to SQL — but users
often want narrative answers, not just maps.

### Active approaches

- **Grounding via spatial databases**: Always execute a spatial query; never
  allow the LLM to reason about coordinates from memory. Scout does this.
- **Hybrid Mind** (IJGIS, April 2025): Integrates algorithmic constraint solvers
  with LLMs for spatial cognition
- **Spatial-RAG** (Yu et al., February 2025): Gives LLMs access to external
  spatial knowledge through geodesic distance graphs and spatial SQL databases
- **Chain-of-Symbol prompting**: Converts spatial problems into symbolic
  representations before reasoning
- **Spatial fact-checking agents**: A secondary agent that verifies spatial
  claims with database calls before the main agent uses them
- **Geospatial benchmarks**: GeoEval, GPSBench, GeoGramBench, GeoAnalystBench
  are starting to standardize evaluation (see Section 15)

---

## 8. Coordinate Reference System Heterogeneity

You used WGS84 (EPSG:4326) throughout Scout. The real world doesn't cooperate.

- US state plane systems (EPSG:2227 for California north)
- UK National Grid (EPSG:27700)
- UTM zones (different zones for different parts of the world)
- Custom CRS definitions in legacy enterprise data

When you build a schema RAG system that retrieves metadata across heterogeneous
datasets, embedding descriptions of those datasets doesn't encode their CRS. A
query for "buildings within 100m of a river" applied to data in meters (UTM) and
data in degrees (WGS84) produces silently wrong results.

Current production systems either:

- Enforce a single CRS at ingestion (Scout's approach — re-project everything to
  WGS84 during ETL), or
- Use ST_Transform at query time (slower, requires CRS metadata to be accurate)

A schema RAG system that also retrieves and applies CRS metadata at query time
doesn't exist as a packaged tool. It's a product gap.

---

## 9. Temporal Geospatial Semantics

"The old warehouse district near the river" — the user wants current buildings
in an area that used to be a warehouse district. This requires:

1. Knowing what "old warehouse district" means historically (temporal semantics)
2. Knowing that "near the river" means the current geographic river location
3. Knowing which buildings currently occupy that area (current spatial data)

Current geospatial AI systems handle snapshot data — a single timestamp.
Temporal querying (give me places as they existed in 2010) requires either:

- Versioned GeoParquet datasets (Overture releases are versioned — this helps)
- Temporal SPARQL (GeoSPARQL has limited temporal support)
- Combining current spatial data with historical text sources (research
  frontier)

The research area of **temporal knowledge graphs** — graphs that encode when
facts were true — is active but not yet productized for geospatial use cases.
Wikidata has temporal edges; applying this to fine-grained spatial queries at
city scale remains unsolved.

---

## 10. Vagueness, Uncertainty, and Imprecise Geographies

### The crispness trap

Traditional GIS software was built on the assumption of crisp boundaries: a
point is exactly _here_, and a polygon boundary divides the world into binary
_inside_ and _outside_.

Human spatial cognition and natural language do not work this way. Consider:

- **Vernacular regions**: Where exactly are the boundaries of "The Midwest",
  "Silicon Valley", or "Downtown"? These are gradient concepts; you are
  definitely in Downtown, or definitely not, but there is a fuzzy transition
  zone.
- **Imprecise features**: "The Alps" or "The Sahara" do not have standardized,
  universally agreed-upon polygon coordinates.
- **Sensor uncertainty**: Every GPS reading has an error radius. Remote sensing
  pixels contain mixed land covers.

### Why AI struggles

When a user asks a geospatial AI system to "find properties in the Bay Area,"
the system typically maps "Bay Area" to a crisp multipolygon from a database
(like Wikidata or OSM) and performs a binary `ST_Intersects` operation. This
fails at the margins—excluding perfect matches that sit 10 meters outside the
arbitrary polygon boundary.

Conversely, if the AI attempts to reason about these places amorphously without
a database geometry, it risks the hallucination trap described earlier. We lack
robust, standardized ways to encode spatial probability distributions (e.g.,
"there is a 90% chance this point is considered 'Downtown'") into standard
spatial query languages.

### Uncertainty quantification: mostly ignored, critically needed

Beyond vague place names, there is a broader UQ problem for geospatial AI
outputs. A _Nature Communications_ scoping review (December 2024) found that
**many researchers do not consider uncertainty in ML-based geospatial
modeling**, and no straightforward criteria exist for evaluating or reducing it.

Promising advances:

- **GeoConformal Prediction** (Lou, Luo, Meng; _Annals AAG_, 2025): A
  model-agnostic framework with distribution-free, finite-sample coverage
  guarantees
- **GeoXCP** (_IJGIS_, October 2025): Uncertainty quantification for explainable
  AI using spatially adaptive conformal prediction
- **UQGNN** (SIGSPATIAL 2025): Graph neural networks for multivariate
  spatiotemporal prediction with probabilistic uncertainty

Adoption in operational geospatial systems remains minimal. For disaster
response, climate adaptation, and defense applications, this is a critical gap.

---

## 11. Qualitative Spatial Reasoning (QSR) and Topological Logic

### Moving beyond coordinates

Humans are terrible at coordinate geometry but excellent at topology. If you
place a cup of coffee on a desk, you intuitively know that if you move the desk,
the cup moves with it. You understand the topological relationship _SupportedBy_
or _Inside_.

In artificial intelligence, **Qualitative Spatial Reasoning (QSR)** seeks to
formalize these relationships using pure logic rather than coordinate math. The
most famous framework is **RCC8 (Region Connection Calculus)**, which defines 8
mutually exclusive topological relations between two regions (e.g.,
Disconnected, Externally Connected, Partially Overlapping, Tangential Proper
Part, etc.).

### The gap in modern AI

Current GeoAI systems are overwhelmingly quantitative. They translate natural
language into SQL functions like `ST_Contains` and let the database compute the
coordinate math. But for "moonshot" applications—like autonomous robots
navigating a disaster zone from verbal instructions, or AI generating entirely
new city layouts—the system needs to reason qualitatively.

LLMs currently struggle to build coherent internal world models based on
topological rules without falling back to a physics engine or a spatial DB.
Bridging the formal logic of QSR with the probabilistic nature of LLMs is a
highly active research area.

---

## 12. The Modifiable Areal Unit Problem (MAUP) and Scaling

### The statistical illusion of spatial aggregation

When querying or analyzing spatial data, we almost always aggregate points into
polygons: grouping crime incidents by census tract, or foot traffic by H3
hexbins (see ).

The **Modifiable Areal Unit Problem (MAUP)** is a statistical bias stating that
your analysis results will change—sometimes dramatically—depending on the shape,
size, and scale of the polygons you choose to aggregate into.

- **Scale effect**: Analyzing data at the county level yields different
  correlations than at the census block level.
- **Zonation effect**: Shifting the boundaries of the zones (like political
  gerrymandering) alters the statistical outcome, even if the underlying point
  data remains identical.

### PM implication

If your AI product generates insights ("crime is highly correlated with liquor
licenses in these neighborhoods"), the AI is likely unaware that those
correlations might evaporate if the grid size changes from res-8 to res-9 H3
cells. Automated GeoAI systems that don't proactively control for MAUP risk
surfacing statistical illusions as actionable insights. Building "MAUP-aware"
spatial AI remains a massive open challenge.

---

## 13. Privacy, Ethics, and Governance

### The data moat vs. individual privacy

The most valuable geospatial AI applications rely on high-resolution Human
Mobility Data (HMD) — anonymized cell phone pings that show where groups of
people go. However, as AI deanonymization techniques improve, releasing such
datasets securely is becoming impossible. Even coarse spatial data can uniquely
identify individuals given enough temporal points.

The mobility analytics landscape has fragmented: SafeGraph discontinued mobility
data (now Advan Research) and pivoted to POI/transaction data. Placer.ai,
Unacast, and pass_by fill the gap, but all face growing regulatory pressure from
GDPR, the EU AI Act, and proliferating U.S. state privacy laws. CARTO's
architectural response — pushing all computation into the customer's data
warehouse so "data never leaves" — is becoming a product differentiator.

### Surveillance capabilities outpace governance

High-resolution EO (16cm SAR from ICEYE, 30cm optical from Pléiades Neo, 35cm
from BlackSky Gen-3) combined with ubiquitous location tracking creates
surveillance capabilities that outpace governance frameworks. The **Locus
Charter** (American Geographical Society's EthicalGEO) provides global
principles covering privacy, bias, do-no-harm, and protecting vulnerable
populations. The AAG GeoEthics Project has identified four focus areas:
surveillance, DEI, data quality/bias, and professional practice.

### The environmental cost irony

A _Nature Machine Intelligence_ paper (2025) highlighted that training massive
geospatial foundation models consumes significant energy — despite their climate
monitoring purpose. The concentration of GeoFM development in a few
well-resourced organizations (Google, IBM, ESA, NASA) raises equity concerns
about who controls planetary-scale spatial intelligence.

### Federated learning & differential privacy

**Federated Spatial Learning** remains the leading technical approach: AI models
trained at the edge with only model weights aggregated globally. Doing this
securely while accounting for spatial autocorrelation and heterogeneous edge
device capabilities is an active research area. Academic advances in
differential privacy (DPDeno framework, HMM-based continuous location privacy)
are moving toward but have not yet reached production-ready implementations.

> For the full landscape of privacy-preserving location analytics and ethical
> frameworks, see the
> [Frontier Report §1: Privacy-Preserving Location
Analytics](/resources/frontier-report-2026).

---

## 14. 3D, Point Clouds, and Multimodal Spatial AI

### The flat Earth problem

Almost all production geospatial AI products focus on 2D data or 2.5D surfaces
(raster elevations). The world, however, is densely 3D.

Currently, reasoning over **LiDAR point clouds**, 3D CityGML models, and Indoor
Mapping data (BIM) requires specialized software (like PDAL or massive CAD
tools) running on heavy compute. This data does not currently fit nicely into
Parquet, nor does it translate smoothly into LLM contexts.

### Industry momentum in 3D

**Bentley Systems acquired Cesium in September 2024** — combining Cesium's open
3D platform (1M+ active devices/month) with Bentley's iTwin infrastructure
digital twin platform. CesiumJS now supports Gaussian splats, imagery draping on
3D Tiles, and Mars data. **NVIDIA's Omniverse** Smart City AI Blueprint provides
reference architecture for physical AI in cities, with deployments processing
50,000+ video streams in real-time.

City-scale digital twins are operational in Singapore (the gold standard),
Helsinki (modeling building retrofit carbon impacts), Seoul (600,000+
buildings), and dozens of others. The indoor positioning market reached a
standards milestone with **IndoorGML 2.0** (August 2025).

### Moonshot barriers

A true spatial AI moonshot might involve a prompt like: _"Find all commercial
buildings in Chicago with flat roofs capable of supporting 50 solar panels,
where the HVAC systems do not block the southern exposure."_

This query cannot be answered with 2D PostGIS polygons. It requires the AI model
to fuse multimodal data — parsing 3D geometry alongside semantic visual data —
while streaming petabytes of point cloud datasets natively. Recent benchmarks
have found multimodal models dropping to near-zero accuracy on 3D spatial
reasoning tasks. SpatialLM and SpatialThinker (reinforcement learning with
spatial rewards) represent the most promising research directions.

---

## 15. The Evaluation Benchmark Gap

How do you know if your NL-to-SQL geospatial system is actually correct?

For text-to-SQL in general, benchmarks like Spider and BIRD exist. They compare
generated SQL to gold-standard SQL on held-out databases.

For **geospatial** NL-to-SQL, no widely-adopted benchmark existed as of early
2025 — but the landscape is rapidly improving:

- **GeoAnalystBench** (2025): Measures validity on Python GIS tasks; frontier
  models substantially outperform open-source models
- **GPSBench** (February 2026): 57,800 samples across 17 spatial tasks
- **GEO-Bench**: Standard benchmark for remote sensing foundation models
- **PANGAEA**: Multi-model comparison benchmark for GeoFMs

The fundamental challenges remain:

- **Result equivalence is spatial, not string-based**: Two SQL queries that
  produce geometrically identical results may look completely different as text.
  Standard string-matching evaluation doesn't work.
- **Spatial tolerance**: Is a polygon that's 3 meters off "correct"? That
  depends on the use case.
- **Natural language ambiguity**: "Near the park" is genuinely ambiguous —
  there's no single gold answer.

Additional active work: GeoEval (2024), NL4Geo (workshop at ACM SIGSPATIAL
2024), and internal benchmarks at companies like Esri and Felt. The field is
moving toward standardization but has not yet had its "ImageNet moment."

For a PM, the improving-but-fragmented benchmark landscape means you can start
to compare approaches — but should still rely on user satisfaction and
task-specific evaluation over any single benchmark score.

---

## 16. Where to Follow the Research

### Conferences

| Venue              | Focus                                                                                             | Cadence              |
| ------------------ | ------------------------------------------------------------------------------------------------- | -------------------- |
| **ACM SIGSPATIAL** | Premier academic geospatial conference; most NL-to-GeoSQL and spatial AI papers appear here first | November annually    |
| **GIScience**      | Geographic information science; more theoretical                                                  | Biennial             |
| **ISWC**           | Semantic web, includes GeoSPARQL and knowledge graph spatial work                                 | October annually     |
| **VLDB / SIGMOD**  | Database systems; DuckDB spatial, GeoParquet performance, query planning                          | July / June annually |

### Working groups to watch

- **OGC GeoAI Pilot** — Ongoing pilots testing LLM integration with OGC APIs;
  reports published after each pilot phase
- **OGC GeoSPARQL SWG** — The standards working group for GeoSPARQL; meeting
  notes and drafts are public
- **OGC GeoZarr SWG** — Formalizing cloud-native gridded data encoding
- **STAC community** — Active Slack and GitHub; real practitioners discussing
  real problems; stacspec.org
- **Cloud-Native Geospatial Conference** — Inaugural event Snowbird, Utah, April
  2025; watch for future events

### (Some) related groups (as of 2024)

- **Krzysztof Janowicz** (UC Santa Barbara) — Geographic knowledge graphs,
  spatial semantics, GeoAI, KnowWhereGraph
- **Yao-Yi Chiang** (USC) — Map understanding, historical map AI, spatial NLP
- **Ross Purves** (University of Zurich) — Vague geography, spatial language
- **Zhenlong Li, Huan Ning** (Penn State) — Autonomous GIS framework, GIS
  Copilot, five levels of GIS autonomy
- **Yingjie Hu** (University at Buffalo) — Geographic information retrieval,
  geoparsing
- **Anthropic, Google DeepMind** geospatial teams — Not publishing much yet, but
  hiring in this space is a leading indicator

### arXiv search terms

- `cs.IR + geospatial` — information retrieval for spatial data
- `cs.DB + spatial` — spatial query processing
- `cs.AI + geographic` — geographic knowledge representations
- `GeoLLM`, `SpatialLM`, `GeoQA` — specific research directions

---

## 17. PM Perspective: Which Bets Are Worth Making?

| Problem                           | Horizon                                                                | What to do now                                                                         |
| --------------------------------- | ---------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Foundation model adoption         | Now — fine-tuning is the new baseline                                  | Evaluate GeoFMs for your domain; budget for fine-tuning and ground truth               |
| Agentic GIS / autonomous analysis | Routine tasks near-term; complex multi-step analysis is longer-horizon | Build agent-compatible interfaces (MCP); product value shifts to orchestration         |
| Ground truth bottleneck           | Ongoing; worse for underrepresented geographies                        | Validate GeoFM outputs for your geography; don't assume global models work locally     |
| OGC API adoption                  | 3-5 years in enterprise                                                | Build on STAC; add OGC API as secondary interface when clients ask                     |
| Geospatial semantic similarity    | 2-3 years to deployable tools                                          | Use two-step SQL + vector retrieval as interim                                         |
| GeoSPARQL graph explosion         | Ongoing; partial fixes available                                       | Avoid raw SPARQL if you can; pre-compute spatial joins into Parquet                    |
| LLM spatial reasoning             | Fundamental architectural limit; hybrid approaches 2028+               | Always route to SQL; never let LLM reason from training data about coordinates         |
| CRS heterogeneity                 | Solvable now with engineering discipline                               | Standardize to WGS84 at ETL time; document CRS in STAC metadata                        |
| Temporal geospatial               | 5+ year research horizon                                               | Versioned releases (Overture model) are the pragmatic solution                         |
| Vagueness and UQ                  | 3-5 years for probabilistic spatial DBs                                | Apply `ST_Buffer` for fuzzy edges; track GeoConformal Prediction research              |
| Qualitative logic (QSR)           | 5-10 year AI reasoning horizon                                         | Delegate topological operations to PostGIS; don't rely on LLM logic                    |
| MAUP and aggregation bias         | Solvable with domain expertise                                         | Lock to single grid system (e.g., H3); visualize multiple scales                       |
| Privacy & ethics                  | Regulatory pressure accelerating now                                   | Adopt data-never-leaves architectures; follow Locus Charter principles                 |
| Evaluation benchmarks             | Improving; 1-2 years to community consensus                            | Use GeoAnalystBench + your own eval set from real user queries                         |
| AI workforce displacement         | Happening now; accelerating                                            | GeoAI specialist roles growing significantly faster than traditional GIS analyst roles |

The pattern: **solve with engineering today what research is still figuring
out**. The products that win are not the ones that wait for the benchmark —
they're the ones that define the benchmark by being deployed and gathering real
user data.
