"""
Scout Backend — Exercise 1: Test the Prompt in Isolation
=========================================================

Validates that the LLM system prompt produces correct DuckDB SQL for our
GeoParquet dataset — before wiring anything into the Next.js API route.

This is how ML engineers iterate on prompts: small script, tight feedback
loop, independent of the web stack.

What it does:
  1. Reads the STAC item JSON (produced by a previous STAC module)
  2. Builds the system prompt from the STAC metadata
  3. Runs each test query through the LLM
  4. Prints the generated SQL and token usage for each

Requirements:
  Set one of these environment variables (or add to a .env file here):
    ANTHROPIC_API_KEY=sk-ant-...    (for LLM_PROVIDER=claude)
    OPENAI_API_KEY=sk-...           (for LLM_PROVIDER=openai)

Run:
  cd src/exercises/24-scout-backend/
  export LLM_PROVIDER=claude        # or: openai
  export ANTHROPIC_API_KEY=sk-ant-...
  uv run python 01_test_prompt.py

  # Or pass a custom query:
  uv run python 01_test_prompt.py --query "Show me breweries in the Mission"
"""

import json
import os
import sys
import argparse
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# The STAC item produced by a previous STAC module
STAC_ITEM_PATH = (
    Path(__file__).parent.parent
    / "23-scout-etl"
    / "output"
    / "stac"
    / "sf-places"
    / "sf-places-2026"
    / "sf-places-2026.json"
)

# Test queries — run all of these unless --query is passed
DEFAULT_TEST_QUERIES = [
    "Show me coffee shops near Dolores Park",
    "Find all breweries in San Francisco",
    "Show me places to eat near the Embarcadero",
    "Show me parks and playgrounds in the Richmond",
    "Find sushi restaurants", # category doesn't exist — watch what happens
    "show me places to eat" # This is ambiguous – see how the model responds.
]

# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def load_stac_item(path: Path) -> dict:
    """Load and validate the STAC item JSON."""
    if not path.exists():
        print(f"ERROR: STAC item not found at {path}")
        print("Run src/exercises/23-scout-etl/03_build_stac_catalog.py first.")
        sys.exit(1)
    with open(path) as f:
        return json.load(f)


def build_system_prompt(item: dict) -> str:
    """
    Build the LLM system prompt from STAC metadata.

    The three components are:
      1. Schema — column names + types (prevents column hallucination)
      2. Categories — closed vocabulary (prevents category hallucination)
      3. DuckDB rules — function syntax + output constraints
    """
    props = item["properties"]
    schema: dict[str, str] = props["scout:schema"]
    categories: list[str] = props["scout:categories"]
    table_name: str = props["scout:table_name"]
    duckdb_notes: str = props["scout:duckdb_notes"]
    row_count: int = props["scout:row_count"]

    schema_block = "\n".join(
        f"  {col:<12} -- {desc}"
        for col, desc in schema.items()
    )

    category_block = ", ".join(categories)

    return f"""You are a SQL query generator for a DuckDB database.

The database contains a single table named '{table_name}' with {row_count:,} rows of San Francisco points of interest from Overture Maps.

## Schema

{schema_block}

## Valid category values

Use ONLY the following values for the `category` column — no other values exist
in the data. If the user asks for something not on this list, choose the closest
match or combine multiple valid categories with OR.

{category_block}

## DuckDB spatial notes

{duckdb_notes}

## Output rules

- Return ONLY a valid DuckDB SQL SELECT statement. No explanation, no markdown
  code fences, no commentary — just the raw SQL.
- Always include: LOAD spatial; as the first statement on its own line.
- Use ST_DWithin for proximity queries. Default radius: 0.005 degrees (~500m).
- LIMIT results to 200 rows unless the user specifies otherwise.
- Never generate INSERT, UPDATE, DELETE, DROP, or CREATE statements.
- If the query is ambiguous, make a reasonable spatial assumption and proceed."""


# ---------------------------------------------------------------------------
# LLM callers
# ---------------------------------------------------------------------------

def call_claude(system_prompt: str, user_query: str) -> tuple[str, dict]:
    """Call Anthropic Claude and return (sql, usage)."""
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=system_prompt,
        messages=[{"role": "user", "content": user_query}],
    )

    sql = message.content[0].text.strip() if message.content[0].type == "text" else ""
    usage = {
        "input_tokens": message.usage.input_tokens,
        "output_tokens": message.usage.output_tokens,
    }
    return sql, usage


def call_openai(system_prompt: str, user_query: str) -> tuple[str, dict]:
    """Call OpenAI GPT-4o and return (sql, usage)."""
    import openai

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set.")
        sys.exit(1)

    client = openai.OpenAI(api_key=api_key)
    completion = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=512,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query},
        ],
    )

    sql = completion.choices[0].message.content or ""
    sql = sql.strip()
    usage = {
        "input_tokens": completion.usage.prompt_tokens,
        "output_tokens": completion.usage.completion_tokens,
    }
    return sql, usage


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # Load environment variables from either:
    #   1. .env in this exercise directory  (local override)
    #   2. .env.local at the project root   (Next.js convention — same file pnpm dev uses)
    # Later files don't overwrite keys already set, so local .env wins if both exist.
    try:
        from dotenv import load_dotenv
        # Project root is 4 directories up: 24-scout-backend/ → exercises/ → src/ → root
        project_root = Path(__file__).parent.parent.parent.parent
        load_dotenv(project_root / ".env.local")          # Next.js root file
        load_dotenv(Path(__file__).parent / ".env")        # local exercise override
    except ImportError:
        pass  # python-dotenv optional; set env vars in shell instead

    parser = argparse.ArgumentParser(description="Test Scout LLM prompt in isolation")
    parser.add_argument(
        "--query",
        help="Single natural language query to test (default: run all test queries)",
    )
    args = parser.parse_args()

    provider = os.environ.get("LLM_PROVIDER", "claude").lower()
    queries = [args.query] if args.query else DEFAULT_TEST_QUERIES

    # --- Load STAC item and build prompt ---
    print("=" * 65)
    print("Scout Exercise 1: Prompt Isolation Test")
    print("=" * 65)

    item = load_stac_item(STAC_ITEM_PATH)
    props = item["properties"]
    system_prompt = build_system_prompt(item)

    print(f"  STAC item    : {STAC_ITEM_PATH.name}")
    print(f"  Row count    : {props['scout:row_count']:,}")
    print(f"  Categories   : {len(props['scout:categories'])}")
    print(f"  Provider     : {provider}")
    print(f"  Queries      : {len(queries)}")
    print()

    # --- Sanity-check: show token estimate for system prompt ---
    # Rough estimate: ~4 chars per token
    estimated_system_tokens = len(system_prompt) // 4
    print(f"  System prompt length : ~{estimated_system_tokens:,} tokens (rough estimate)")
    print(f"  (This is the fixed cost you pay on every query.)")
    print()

    # --- Run each query ---
    call_fn = call_claude if provider == "claude" else call_openai
    total_input = 0
    total_output = 0

    for i, query in enumerate(queries, 1):
        print(f"{'─' * 65}")
        print(f"Query {i}/{len(queries)}: {query}")
        print()

        try:
            sql, usage = call_fn(system_prompt, query)
        except Exception as exc:
            print(f"  ERROR: {exc}")
            continue

        total_input += usage["input_tokens"]
        total_output += usage["output_tokens"]

        print("SQL output:")
        print()
        # Indent each line for readability
        for line in sql.split("\n"):
            print(f"  {line}")
        print()
        print(f"  Tokens — input: {usage['input_tokens']:,}  output: {usage['output_tokens']:,}")
        print()

    # --- Summary ---
    print("=" * 65)
    print(f"Total tokens used across {len(queries)} queries:")
    print(f"  Input  : {total_input:,}")
    print(f"  Output : {total_output:,}")
    print(f"  Total  : {total_input + total_output:,}")
    print()
    print("Note: Input tokens are dominated by the system prompt.")
    print("Each query pays this fixed cost.")
    print("Stuffing Breaks Down for what happens when the prompt grows.")
    print("=" * 65)


if __name__ == "__main__":
    main()
