> Status: Elective / Extended Module — complete the elective modules first.

## Overview

Vector-schema RAG replaces Scout's prompt-stuffing approach with a genuine retrieval pipeline for scenarios where many datasets with unknown schemas must be supported. Schema documentation — table names, column descriptions, spatial types, category vocabularies — is embedded into a vector database and retrieved by semantic similarity at query time. This prevents LLMs from hallucinating column names and table relationships, and reduces prompt token count by only injecting the schemas relevant to the user's question.

## Key Concepts

### 1. Schema-as-Document Embedding

Each dataset's schema is split into fine-grained text chunks — title/description, individual field definitions, category vocabulary — and embedded using a sentence-transformer model. STAC catalog items are the natural input: they already contain structured metadata written in human-readable prose. No manual description generation is required; you embed what the catalog already says.

### 2. Retrieval to Prevent Hallucination

When a user asks a question, the query is embedded and compared against all schema chunks in the vector store. The top-k most semantically similar chunks are retrieved and injected into the system prompt. The LLM receives only the schemas relevant to the question, which eliminates both the context-window overflow problem (60 schemas × full schema text) and the retrieval noise problem (irrelevant column names confusing SQL generation).

### 3. Grounded SQL Generation

With retrieved schema chunks injected, the LLM generates SQL against column names and vocabulary values that actually exist in the database. Synonym routing is a key benefit: querying "show me drugstores" retrieves the same `category_vocabulary` chunk as "show me pharmacies" because their embeddings are semantically close — no hardcoded synonym list required.

## 1. The Scale Problem

Imagine Scout deployed at a city's Open Data Portal. Instead of one GeoParquet,
there are 60 datasets: parcels, zoning, tree inventory, traffic sensors, bike
lanes, inspection records, permit history, flood zones... Each has its own
schema, its own column names, its own vocabulary.

The prompt stuffing approach fails here for two reasons:

- **Context window overflow**: Even if all 60 schemas fit in a 200K-token window
  today, you're paying for all 60 schemas on every single query. Most queries
  are about one dataset.
- **Retrieval noise**: Injecting irrelevant schema context actively degrades SQL
  generation quality — the model gets confused by columns that don't apply to
  the user's intent.

The right approach is to **retrieve before you inject**: find the 2-3 schemas
that are most relevant to the user's question, then build a minimal, targeted
prompt.

## 2. How Vector Search Solves It

Vector embeddings turn text into numerical arrays ("vectors") that encode
semantic meaning. Sentences with similar meaning get vectors that are close in
space, regardless of exact word choice.

The workflow: offline, embed each STAC catalog item's schema chunks into a
vector database. At query time, embed the user's question, perform semantic
similarity search to retrieve the top-k most relevant schema chunks, inject
those chunks into the system prompt, and call the LLM. The LLM generates SQL
with accurate column names because it only receives schemas that match the
question.

This is the same pattern used by Vanna AI (open source Text-to-SQL with RAG),
Databricks Genie (natural language over data lakehouses), Snowflake Copilot
(NL-to-SQL over Snowflake catalogs), and Esri's ArcGIS Assistant (NL over GIS
layers).

The geospatial-specific insight: STAC catalogs are already structured metadata —
they're the natural embedding input. You don't need to generate descriptions
from scratch; you embed the STAC item summaries, keywords, and column
descriptions you already wrote in Phase 1.

## 3. Why This Matters for Product Patterns

This module represents a major product expansion decision:

- **From a tool to a platform**: Prompt stuffing makes Scout a single-dataset
  tool. RAG makes it a platform that can onboard new datasets without touching
  the application code. New dataset → run ETL → add to vector index → done.
- **The "data catalog" as a product**: The vector database becomes a living,
  searchable index of everything the system knows. This is the same concept
  behind Alation, Atlan, and DataHub — data cataloging platforms that GIS
  organizations pay serious money for.
- **Cost optimization**: Retrieving 3 relevant schemas instead of injecting 60
  reduces prompt token count by 95%+. At scale, this is the difference between a
  viable and an unviable cost structure.
- **The cold start problem**: When users onboard a new dataset, how does the
  system know what questions it can answer? The vector index enables "similarity
  by analogy" — a new "tree_inventory" dataset is automatically queryable for
  tree-related questions because its embeddings are close to similar datasets.

## 5. Exercises

The exercise directory at `src/exercises/vector-rag/` contains three scripts:
`01_embed_catalog.py` builds a ChromaDB index from the Phase 1 STAC catalog,
`02_retrieval_compare.py` runs side-by-side token count and SQL quality
comparisons between prompt-stuffing and RAG, and `03_onboard_buildings.py` adds
a second dataset (Overture buildings) to the index and exports a
`retrieval_index.json` snapshot for the Next.js API route.

### Exercise 1: Embed the STAC Catalog

Reads the STAC catalog from Phase 1, splits each dataset into fine-grained
chunks (title/description, schema fields, category vocabulary), and embeds them
using `sentence-transformers/all-MiniLM-L6-v2` — fully local, no API key.
Stores vectors in a persistent ChromaDB instance at `output/chroma/`.

### Exercise 2: Retrieval vs. Prompt Stuffing

Requires `LLM_PROVIDER` and an API key set in your environment. Runs 6 test
queries through both pipelines and prints a comparison table showing token count
reduction (prompt-stuffing vs. RAG) and the synonym test — querying "pharmacy"
and "drugstore" should retrieve the same schema chunk.

### Exercise 3: Onboard a Second Dataset

Adds an Overture Maps buildings dataset to the index without running any ETL.
Runs routing disambiguation tests to verify that `"coffee shop near a park"`
routes to the `places` dataset and `"tall buildings in SoMa"` routes to the
`buildings` dataset. Exports `output/retrieval_index.json` — a flat JSON
snapshot that the Next.js RAG API route reads at query time.

### What to Observe

- **Semantic routing**: Query "show me pharmacies" then "show me drugstores".
  Both retrieve the same `sf-places-2026:category_vocabulary` chunk — no
  synonyms list needed.
- **Token delta**: Log prompt token counts shown in the comparison table. The
  reduction is your cost-per-query improvement at scale.
- **Retrieval failures**: Ask about something not in the index. The LLM should
  use `LIKE '%keyword%'` on the name column (graceful fallback).

### Scout UI: RAG Toggle

After running Exercise 3, toggle to **RAG mode** on the `/scout` page. The
bottom panel gains a green-themed mode indicator and a "Retrieved schema chunks"
panel showing exactly which chunks were selected for your query (with similarity
scores). Compare the same query in both modes to see the token count difference
live.

---

## 6. Tooling Landscape

| Tool                  | Type            | Best for                                     | Self-hosted? |
| --------------------- | --------------- | -------------------------------------------- | ------------ |
| ChromaDB              | Vector DB       | Local dev, notebooks, quick prototypes       | Yes          |
| Qdrant                | Vector DB       | Production, spatial payload filtering        | Yes or Cloud |
| pgvector              | Postgres ext    | Existing Postgres infra, hybrid with PostGIS | Yes          |
| Weaviate              | Vector DB       | Hybrid BM25+vector, rich metadata            | Yes or Cloud |
| Pinecone              | Managed         | Zero ops, large scale                        | Cloud only   |
| OpenAI embeddings     | Embedding model | Highest quality, requires API                | No           |
| sentence-transformers | Embedding model | Local, no cost, good quality                 | Yes          |

For learning: start with ChromaDB + `sentence-transformers`. Zero servers, zero
cost, runs in the same `uv` environment.

## Practical Exercises


