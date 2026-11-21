"""
Exercise 2: Retrieval vs. Prompt Stuffing Comparison
=======================================================================

Runs the same 6 test queries from the NL-to-SQL exercise through BOTH pipelines:
  1. Stuffing: inject the full STAC catalog (Baseline)
  2. RAG:      embed the query → retrieve top-K chunks → targeted prompt

Prints a side-by-side comparison table of:
  - Input token count (stuffing vs. RAG)
  - Which chunks were retrieved (RAG only)
  - SQL output (both)

Key things to watch:
  - Synonym routing: "pharmacy" and "drugstore" should retrieve the same chunk
  - Out-of-vocab test: "sushi restaurant" doesn't exist — see what happens
  - Token delta: should be 80–90% reduction from stuffing to RAG

Run:
    cd src/exercises/
    export LLM_PROVIDER=claude   # or openai
    export ANTHROPIC_API_KEY=sk-ant-...
    uv run python vector-rag/02_retrieval_compare.py

Requires:
    01_embed_catalog.py must have been run first (output/chroma/ must exist).
"""

import json
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

STAC_ITEM_PATH = (
    Path(__file__).parent.parent
    / "scout-etl"
    / "output"
    / "stac"
    / "sf-places"
    / "sf-places-2026"
    / "sf-places-2026.json"
)

CHROMA_DIR = Path(__file__).parent / "output" / "chroma"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = "scout_schema_chunks"

# Same queries as the NL-to-SQL exercise for direct comparison
TEST_QUERIES = [
    "Show me coffee shops near Dolores Park",
    "Find all breweries in San Francisco",
    # Synonym test — pharmacy vs. drugstore
    "Find pharmacies",
    "Find drugstores",          # should retrieve same chunk as "pharmacies"
    # Out-of-vocab — reveals graceful failure
    "Find sushi restaurants",
    # Ambiguous
    "show me places to eat",
]

TOP_K = 3  # number of chunks to retrieve


# ---------------------------------------------------------------------------
# Stuffing prompt builder (copy from NL-to-SQL)
# ---------------------------------------------------------------------------

def build_stuffing_prompt(item: dict) -> str:
    props = item["properties"]
    schema: dict[str, str] = props["scout:schema"]
    categories: list[str] = props["scout:categories"]
    table_name: str = props["scout:table_name"]
    duckdb_notes: str = props["scout:duckdb_notes"]
    row_count: int = props["scout:row_count"]

    schema_block = "\n".join(
        f"  {col:<12} -- {desc}" for col, desc in schema.items()
    )
    category_block = ", ".join(categories)

    return f"""You are a SQL query generator for a DuckDB database.
The database contains a single table named '{table_name}' with {row_count:,} rows of SF points of interest.

## Schema
{schema_block}

## Valid category values
{category_block}

## DuckDB spatial notes
{duckdb_notes}

## Output rules
- Return ONLY a valid DuckDB SQL SELECT statement. No markdown, no explanation.
- Always: LOAD spatial; on its own first line.
- LIMIT 200 rows. SELECT id, name, category, lat, lon at minimum.
- Never generate INSERT/UPDATE/DELETE/DROP/CREATE."""


# ---------------------------------------------------------------------------
# RAG prompt builder
# ---------------------------------------------------------------------------

def build_rag_prompt(retrieved_chunks: list[dict]) -> tuple[str, list[dict]]:
    """
    Build a targeted prompt from only the retrieved schema chunks.
    Returns (prompt_text, retrieved_chunk_info_list).
    """
    # Gather what we need from retrieved metadata
    tables: dict[str, dict] = {}
    category_blocks: list[str] = []
    duckdb_notes_seen: set[str] = set()

    chunk_info = []

    for chunk in retrieved_chunks:
        meta = chunk["metadata"]
        ctype = meta.get("chunk_type", "")
        dataset = meta.get("dataset_id", "?")

        chunk_info.append({
            "dataset": dataset,
            "chunk_type": ctype,
            "text_preview": chunk["document"][:80] + "...",
            "similarity": chunk["similarity"],
        })

        if ctype == "schema_fields":
            schema = json.loads(meta.get("schema_json", "{}"))
            table = meta.get("table_name", dataset)
            row_count = meta.get("row_count", 0)
            notes = meta.get("duckdb_notes", "")
            tables[table] = {"schema": schema, "row_count": row_count}
            if notes:
                duckdb_notes_seen.add(notes)

        elif ctype == "category_vocabulary":
            categories = json.loads(meta.get("categories_json", "[]"))
            table = meta.get("table_name", dataset)
            if categories:
                cat_block = f"Valid categories for {table}: " + ", ".join(categories)
                category_blocks.append(cat_block)

    # Build schema section
    schema_section = ""
    for table, info in tables.items():
        schema_section += f"\nTable '{table}' ({info['row_count']:,} rows):\n"
        for col, desc in info["schema"].items():
            schema_section += f"  {col:<12} -- {desc}\n"

    # Build category section
    category_section = "\n".join(category_blocks) if category_blocks else "(no category constraints)"

    # Build DuckDB notes section
    notes_section = "\n".join(duckdb_notes_seen) if duckdb_notes_seen else ""

    prompt = f"""You are a SQL query generator for a DuckDB geospatial database.

## Available Schema (retrieved by semantic similarity)
{schema_section}

## Category constraints
{category_section}

## DuckDB spatial notes
{notes_section}

## Output rules
- Return ONLY a valid DuckDB SQL SELECT statement. No markdown, no explanation.
- Always: LOAD spatial; on its own first line.
- LIMIT 200 rows. SELECT id, name, category, lat, lon at minimum.
- Never generate INSERT/UPDATE/DELETE/DROP/CREATE.
- If no matching category exists, use LIKE '%keyword%' on the name column instead."""

    return prompt, chunk_info


# ---------------------------------------------------------------------------
# LLM callers (same as NL-to-SQL)
# ---------------------------------------------------------------------------

def call_llm(provider: str, system_prompt: str, user_query: str) -> tuple[str, dict]:
    if provider == "openai":
        import openai
        client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        completion = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=512,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query},
            ],
        )
        return (
            (completion.choices[0].message.content or "").strip(),
            {
                "input_tokens": completion.usage.prompt_tokens if completion.usage else 0,
                "output_tokens": completion.usage.completion_tokens if completion.usage else 0,
            },
        )
    else:  # claude
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system=system_prompt,
            messages=[{"role": "user", "content": user_query}],
        )
        sql = msg.content[0].text.strip() if msg.content[0].type == "text" else ""
        return sql, {
            "input_tokens": msg.usage.input_tokens,
            "output_tokens": msg.usage.output_tokens,
        }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    try:
        from dotenv import load_dotenv
        project_root = Path(__file__).parent.parent.parent.parent
        load_dotenv(project_root / ".env.local")
        load_dotenv(Path(__file__).parent / ".env")
    except ImportError:
        pass

    if not STAC_ITEM_PATH.exists():
        print(f"ERROR: STAC item not found. Run the STAC Cataloging exercise first.")
        sys.exit(1)

    if not (CHROMA_DIR / "chroma.sqlite3").exists():
        print(f"ERROR: ChromaDB not found at {CHROMA_DIR}.")
        print("Run 01_embed_catalog.py first.")
        sys.exit(1)

    import chromadb
    from chromadb.utils import embedding_functions

    provider = os.environ.get("LLM_PROVIDER", "claude").lower()

    print("=" * 70)
    print("Exercise 2: Retrieval vs. Prompt Stuffing")
    print("=" * 70)
    print(f"  Provider: {provider}  |  Queries: {len(TEST_QUERIES)}  |  Top-K: {TOP_K}")
    print()

    # Load full STAC item for stuffing baseline
    with open(STAC_ITEM_PATH) as f:
        stac_item = json.load(f)
    stuffing_prompt = build_stuffing_prompt(stac_item)
    stuffing_token_estimate = len(stuffing_prompt) // 4
    print(f"  Stuffing system prompt: ~{stuffing_token_estimate:,} tokens (static cost per query)")
    print()

    # Load ChromaDB
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )
    collection = client.get_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
    )

    summary_rows = []

    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"{'─' * 70}")
        print(f"Query {i}/{len(TEST_QUERIES)}: {query}")
        print()

        # --- RAG retrieval ---
        results = collection.query(
            query_texts=[query],
            n_results=TOP_K,
        )
        retrieved = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            retrieved.append({
                "document": doc,
                "metadata": meta,
                "similarity": round(1 - dist, 3),
            })

        rag_prompt, chunk_info = build_rag_prompt(retrieved)
        rag_token_estimate = len(rag_prompt) // 4

        print(f"  Retrieved chunks ({TOP_K}):")
        for c in chunk_info:
            print(f"    [{c['similarity']:.3f}] {c['dataset']}:{c['chunk_type']}")

        print()
        print(f"  Token estimates — Stuffing: ~{stuffing_token_estimate:,}  |  RAG: ~{rag_token_estimate:,}  "
              f"(reduction: {100*(1-rag_token_estimate/stuffing_token_estimate):.0f}%)")
        print()

        # --- Call LLM with RAG prompt ---
        try:
            sql, usage = call_llm(provider, rag_prompt, query)
            print(f"  RAG SQL ({usage['input_tokens']} actual input tokens):")
            for line in sql.splitlines():
                print(f"    {line}")
            print()
        except Exception as e:
            sql = ""
            usage = {"input_tokens": 0, "output_tokens": 0}
            print(f"  LLM ERROR: {e}")

        summary_rows.append({
            "query": query,
            "stuffing_est": stuffing_token_estimate,
            "rag_actual": usage["input_tokens"],
            "chunks": [f"{c['dataset']}:{c['chunk_type']}" for c in chunk_info],
        })

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  {'Query':<42} {'Stuffing':>10} {'RAG':>8} {'Reduction':>10}")
    print(f"  {'─'*42} {'─'*10} {'─'*8} {'─'*10}")
    for row in summary_rows:
        q = row["query"][:40]
        s = row["stuffing_est"]
        r = row["rag_actual"]
        red = f"{100*(1-r/s if s else 0):.0f}%" if r > 0 else "N/A"
        print(f"  {q:<42} {s:>10,} {r:>8,} {red:>10}")

    print()
    print("Next: Run 03_onboard_buildings.py to add a second dataset")
    print("      and export retrieval_index.json for the Next.js API route.")
    print("=" * 70)


if __name__ == "__main__":
    main()
