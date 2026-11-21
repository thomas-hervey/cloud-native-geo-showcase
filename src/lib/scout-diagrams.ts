/**
 * Scout Architecture Diagrams — Mermaid generator functions
 * ===========================================================
 * Pure functions that produce Mermaid sequence diagram strings from the
 * shared PIPELINE constants in scout-pipeline.ts.
 *
 * Why this matters:
 *   If you change SIM_THRESHOLD from 0.05 → 0.10, the diagram updates
 *   automatically on next render — no manual diagram maintenance needed.
 *
 * Used by: src/app/scout/components/PipelineDiagram.tsx
 */

import { PIPELINE } from './scout-pipeline';

/**
 * Prompt-stuffing pipeline (Module 25 baseline).
 * Shows: User → UI → API → full STAC catalog read → LLM → DuckDB-Wasm → Map
 */
export function buildStuffingDiagram(): string {
  return `sequenceDiagram
    autonumber
    participant U as 👤 User
    participant UI as Scout UI<br/>(Next.js)
    participant API as /api/scout/query<br/>(server)
    participant STAC as STAC Catalog<br/>(filesystem)
    participant LLM as ${PIPELINE.CLAUDE_MODEL}<br/>(LLM)
    participant DDB as DuckDB-Wasm<br/>(browser)

    Note over U,DDB: Every query — online path only

    U->>UI: Natural language query
    UI->>API: POST { query }

    Note over API,STAC: Prompt stuffing (Module 25)<br/>~${PIPELINE.STUFFING_PROMPT_TOKENS} tokens per call
    API->>STAC: Read full STAC catalog
    STAC-->>API: All dataset schemas + categories

    API->>LLM: system=[full catalog] + user=[query]
    LLM-->>API: DuckDB SQL (max ${PIPELINE.MAX_TOKENS} tokens)
    API-->>UI: { sql, provider }

    UI->>DDB: Execute SQL against ${PIPELINE.PRIMARY_TABLE}.parquet
    DDB-->>UI: GeoJSON features
    UI->>U: Map pins + results table`;
}

/**
 * RAG pipeline (Module 26).
 * Shows the offline index-build phase (Python) and the online query phase
 * (Next.js), with the exact PIPELINE constants embedded in the notes.
 */
export function buildRagDiagram(): string {
  return `sequenceDiagram
    autonumber
    participant PY as 🐍 Python<br/>(offline)
    participant CS as ChromaDB<br/>(${PIPELINE.COLLECTION_NAME})
    participant IDX as retrieval_index.json<br/>(public/data/)
    participant U as 👤 User
    participant UI as Scout UI<br/>(Next.js)
    participant API as /api/scout/rag-query<br/>(server)
    participant LLM as ${PIPELINE.CLAUDE_MODEL}<br/>(LLM)
    participant DDB as DuckDB-Wasm<br/>(browser)

    rect rgb(240, 253, 244)
      Note over PY,IDX: OFFLINE — run once with Exercise 01 + 03
      PY->>CS: Embed STAC chunks (${PIPELINE.EMBEDDING_MODEL})
      Note over PY,CS: title_description · schema_fields · category_vocabulary
      PY->>IDX: Export all vectors as flat JSON<br/>(${PIPELINE.TOP_K * 7}+ dims per chunk)
    end

    rect rgb(239, 246, 255)
      Note over U,DDB: ONLINE — each query
      U->>UI: Natural language query
      UI->>API: POST { query }

      API->>IDX: Load pre-computed embeddings
      Note over API: Score all chunks via keyword overlap<br/>(cosine if OpenAI embedding available)

      API->>API: Fetch top-${PIPELINE.TOP_K} by score
      API->>API: Filter: keep sim ≥ ${PIPELINE.SIM_THRESHOLD}
      Note over API: Filtered chunks returned to UI<br/>for transparency (amber panel)

      API->>LLM: system=[retrieved schemas only] + user=[query]
      Note over API,LLM: Targeted prompt — only relevant chunks
      LLM-->>API: DuckDB SQL (max ${PIPELINE.MAX_TOKENS} tokens)

      API-->>UI: { sql, retrieved_chunks, filtered_chunks, pipeline }
      UI->>DDB: Execute SQL against ${PIPELINE.PRIMARY_TABLE}.parquet
      DDB-->>UI: GeoJSON features
      UI->>U: Map + green chunks panel + amber filter log
    end`;
}

/**
 * Agent pipeline (Module 27).
 * Shows the multi-turn LLM tool loop with max iterations and the four tools.
 */
export function buildAgentDiagram(): string {
  return `sequenceDiagram
    autonumber
    participant U as 👤 User
    participant UI as Scout UI<br/>(Next.js)
    participant API as /api/scout/agent-query<br/>(server)
    participant LLM as ${PIPELINE.CLAUDE_MODEL}<br/>(LLM)
    participant TOOLS as Tool Handlers<br/>(server)
    participant DDB as DuckDB-Wasm<br/>(browser)

    Note over U,DDB: Agent mode — LLM decides which tools to call and in what order

    U->>UI: Natural language query
    UI->>API: POST { query, bbox }

    loop Agent loop (max 6 turns)
      API->>LLM: messages + 4 tool schemas
      LLM-->>API: tool_use block (search_datasets | execute_sql | get_map_extent | ask_clarification)
      Note over LLM,API: stop_reason = tool_use while agent still reasoning
      API->>TOOLS: Execute tool + record span
      TOOLS-->>API: tool_result (schema chunks | SQL result | bbox | clarification)
      API->>LLM: append tool_result, continue loop
    end

    Note over LLM,API: stop_reason = end_turn — agent done
    LLM-->>API: Final DuckDB SQL
    API-->>UI: { sql, reasoning_trace, usage }
    Note over API,UI: reasoning_trace: every tool call with input, output, elapsed_ms

    UI->>DDB: Execute SQL against GeoParquet
    DDB-->>UI: GeoJSON features
    UI->>U: Map + violet reasoning trace panel (collapsible steps)`;
}

