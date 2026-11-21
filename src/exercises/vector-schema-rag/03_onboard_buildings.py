"""
Vector RAG — Exercise 3: Onboard a Second Dataset + Export Retrieval Index
================================================================================

This script demonstrates the key "platform vs. tool" transition enabled by RAG:
adding a new dataset requires no changes to application code — just add it to
the vector index and re-export.

What this script does:
  1. Creates a synthetic STAC item for an Overture Maps buildings dataset
  2. Embeds and upserts it into the same ChromaDB collection
  3. Runs routing disambiguation tests to prove correct dataset selection:
       - "coffee shop near a park"      → should route to places
       - "tall buildings in SoMa"      → should route to buildings
       - "find a pharmacy"             → places (with synonym routing)
  4. Exports retrieval_index.json — a flat JSON snapshot of the ChromaDB
     collection that the Next.js RAG API route reads at query time.

Why export to JSON?
  Next.js cannot call into Python at runtime. The retrieval_index.json stores:
    - Every chunk's text and metadata
    - Every chunk's pre-computed embedding vector
  The Next.js route embeds the user query in TypeScript (using a lightweight
  cosine similarity implementation) and searches this index.
  This is the correct production pattern: Python owns the index pipeline,
  the application layer reads it. Same approach used by Vanna AI and Databricks.

Run:
    cd src/exercises/
    uv run python vector-rag/03_onboard_buildings.py

Requires:
    01_embed_catalog.py must have been run first.

Output:
    vector-rag/output/chroma/         (updated vector store)
    vector-rag/output/retrieval_index.json  (for Next.js to consume)
"""

import json
import sys
from pathlib import Path

CHROMA_DIR = Path(__file__).parent / "output" / "chroma"
OUTPUT_INDEX_PATH = Path(__file__).parent / "output" / "retrieval_index.json"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = "scout_schema_chunks"


# ---------------------------------------------------------------------------
# Synthetic buildings dataset definition
# ---------------------------------------------------------------------------

BUILDINGS_DATASET = {
    "id": "sf-buildings-2026",
    "title": "SF Buildings (Overture Maps)",
    "description": (
        "San Francisco building footprints from Overture Maps 2026 release. "
        "Includes building height, floor count, and use class where available. "
        "Coverage: full city boundary, ~220,000 features."
    ),
    "table_name": "buildings",
    "row_count": 220_000,
    "schema": {
        "id":         "Unique Overture Maps building identifier (string)",
        "height":     "Building height in meters (double, nullable)",
        "floors":     "Number of floors above ground (integer, nullable)",
        "use_class":  "Primary use: residential, commercial, industrial, civic (string, nullable)",
        "geometry":   "WKB-encoded polygon geometry — use ST_GeomFromWKB(geometry) (blob)",
        "lat":        "Centroid latitude, WGS84 (double)",
        "lon":        "Centroid longitude, WGS84 (double)",
    },
    "duckdb_notes": (
        "LOAD spatial; required. "
        "Cast geometry: ST_GeomFromWKB(geometry). "
        "Use ST_Area(ST_GeomFromWKB(geometry)) for footprint area. "
        "Filter tall buildings: WHERE height > 50. "
        "Use ST_DWithin(ST_Point(lon, lat), ST_Point(ref_lon, ref_lat), dist_degrees) for proximity."
    ),
    "bbox": [-122.5152, 37.7079, -122.3591, 37.8324],
    "categories": [],  # buildings don't have category vocab
}


def build_chunks_from_dataset(ds: dict) -> list[dict]:
    """Build embedding chunks from a dataset definition dict."""
    chunks = []
    dataset_id = ds["id"]

    # Chunk 1: title + description
    chunks.append({
        "id": f"{dataset_id}:title_description",
        "text": f"{ds['title']}. {ds['description']}",
        "metadata": {
            "dataset_id": dataset_id,
            "chunk_type": "title_description",
            "bbox_xmin": ds["bbox"][0],
            "bbox_ymin": ds["bbox"][1],
            "bbox_xmax": ds["bbox"][2],
            "bbox_ymax": ds["bbox"][3],
        },
    })

    # Chunk 2: schema fields
    schema_lines = [f"Table: {ds['table_name']} ({ds['row_count']:,} rows)"]
    for col, desc in ds["schema"].items():
        schema_lines.append(f"  {col}: {desc}")
    schema_lines.append(f"DuckDB notes: {ds['duckdb_notes']}")

    chunks.append({
        "id": f"{dataset_id}:schema_fields",
        "text": "\n".join(schema_lines),
        "metadata": {
            "dataset_id": dataset_id,
            "chunk_type": "schema_fields",
            "table_name": ds["table_name"],
            "row_count": ds["row_count"],
            "duckdb_notes": ds["duckdb_notes"],
            "schema_json": json.dumps(ds["schema"]),
        },
    })

    return chunks


# ---------------------------------------------------------------------------
# Export retrieval index (for Next.js)
# ---------------------------------------------------------------------------

def export_retrieval_index(collection, embedding_function) -> None:
    """
    Export the entire ChromaDB collection to a flat JSON file.

    The JSON contains:
      - embeddings: list of {id, document, metadata, embedding} objects
      - model: embedding model name (informational)
      - exported_at: timestamp

    The Next.js API route reads this file, embeds the user query in TypeScript
    (using the same cosine similarity math), and returns the top-K matches.
    """
    import datetime

    print(f"   Fetching all documents + embeddings from ChromaDB...")
    result = collection.get(
        include=["documents", "metadatas", "embeddings"]
    )

    items = []
    for i, doc_id in enumerate(result["ids"]):
        embedding = result["embeddings"][i]
        # ChromaDB returns NumPy ndarrays — convert to plain Python list for JSON
        if hasattr(embedding, "tolist"):
            embedding = embedding.tolist()
        items.append({
            "id": doc_id,
            "document": result["documents"][i],
            "metadata": result["metadatas"][i],
            "embedding": embedding,
        })

    index = {
        "model": EMBEDDING_MODEL,
        "collection": COLLECTION_NAME,
        "exported_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "num_documents": len(items),
        "documents": items,
    }

    OUTPUT_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_INDEX_PATH, "w") as f:
        json.dump(index, f)

    size_kb = OUTPUT_INDEX_PATH.stat().st_size / 1024
    print(f"   Exported {len(items)} documents → {OUTPUT_INDEX_PATH} ({size_kb:.1f} KB)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if not (CHROMA_DIR / "chroma.sqlite3").exists():
        print(f"ERROR: ChromaDB not found at {CHROMA_DIR}.")
        print("Run 01_embed_catalog.py first.")
        sys.exit(1)

    import chromadb
    from chromadb.utils import embedding_functions

    print("=" * 65)
    print("Vector RAG — Exercise 3: Onboard Buildings Dataset")
    print("=" * 65)

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )

    before_count = collection.count()
    print(f"\n  Collection currently has {before_count} documents")

    # -- Step 1: Add buildings dataset --------------------------------------
    print("\n1/3  Onboarding buildings dataset...")
    chunks = build_chunks_from_dataset(BUILDINGS_DATASET)
    collection.upsert(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        metadatas=[c["metadata"] for c in chunks],
    )
    after_count = collection.count()
    print(f"     Added {len(chunks)} chunks. Collection now: {after_count} documents")

    # -- Step 2: Routing disambiguation tests --------------------------------
    print("\n2/3  Routing disambiguation tests...")

    # expected_keyword: a string that should appear in the winning dataset_id
    # e.g. "places" matches "sf-places-2026", "buildings" matches "sf-buildings-2026"
    test_queries = [
        ("coffee shop near a park",    "places",    "semantic: places keywords"),
        ("tall buildings in SoMa",     "buildings", "semantic: height/structure keywords"),
        ("find a pharmacy",            "places",    "semantic: POI/category keywords"),
        ("building footprint area",    "buildings", "semantic: spatial area computation"),
        ("restaurant open late night", "places",    "semantic: dining/POI context"),
    ]

    print(f"\n  {'Query':<40} {'Expected':>10} {'Got (dataset_id)':>22} {'Match':>7}")
    print(f"  {'─'*40} {'─'*10} {'─'*22} {'─'*7}")

    all_correct = 0
    for query, expected_keyword, reason in test_queries:
        results = collection.query(query_texts=[query], n_results=1)
        if not results["ids"][0]:
            got_id = "NONE"
            matched = False
        else:
            got_id = results["metadatas"][0][0].get("dataset_id", "?")
            matched = expected_keyword in got_id
        sim = round(1 - results["distances"][0][0], 3) if results["distances"][0] else 0
        mark = "✓" if matched else "✗"
        if matched:
            all_correct += 1
        print(f"  {query[:40]:<40} {expected_keyword:>10} {got_id:>22} {mark:>7}  (sim={sim:.3f})")

    print(f"\n  Result: {all_correct}/{len(test_queries)} routing tests passed")
    if all_correct < len(test_queries):
        print("  (Some tests may fail if the model requires fine-tuning — this is expected learning material.)")

    # -- Step 3: Export retrieval index for Next.js --------------------------
    print("\n3/3  Exporting retrieval_index.json for Next.js RAG API route...")
    export_retrieval_index(collection, ef)

    print()
    print("=" * 65)
    print("Exercise 3 complete!")
    print()
    print(f"  ChromaDB store : {CHROMA_DIR}")
    print(f"  Retrieval index: {OUTPUT_INDEX_PATH}")
    print()
    print("Next steps:")
    print("  1. Copy retrieval_index.json to public/data/ so Next.js can read it")
    print("  2. Toggle to RAG mode in the Scout UI at /scout")
    print("=" * 65)


if __name__ == "__main__":
    main()
