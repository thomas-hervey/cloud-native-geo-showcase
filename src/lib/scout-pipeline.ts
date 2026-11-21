/**
 * Scout Pipeline — Shared Constants
 * ===================================
 * Single source of truth for pipeline parameters used by:
 *   - /api/scout/rag-query/route.ts   (RAG retrieval)
 *   - /api/scout/query/route.ts       (prompt stuffing, for reference)
 *   - src/app/scout/components/PipelineDiagram.tsx  (architecture diagrams)
 *
 * If you change a value here, both the runtime behavior AND the architecture
 * diagram update automatically.
 */


export const PIPELINE = {
  // ------- RAG retrieval -------
  /** Number of candidates fetched from the index before threshold filtering */
  TOP_K: 5,
  /** Cosine similarity minimum — chunks below this are discarded before prompting */
  SIM_THRESHOLD: 0.05,
  /** Embedding model used by the Python exercises to build the index */
  EMBEDDING_MODEL: 'all-MiniLM-L6-v2',
  /** ChromaDB collection name */
  COLLECTION_NAME: 'scout_schema_chunks',

  // ------- LLM -------
  /** Claude model used by both API routes */
  CLAUDE_MODEL: 'claude-sonnet-4-6',
  /** OpenAI model used as fallback */
  OPENAI_MODEL: 'gpt-4o',
  /** Max SQL tokens */
  MAX_TOKENS: 512,

  // ------- Data -------
  /** Primary dataset available in DuckDB-Wasm */
  PRIMARY_DATASET: 'sf-places-2026',
  /** Primary table name in DuckDB SQL */
  PRIMARY_TABLE: 'places',
  /** Secondary dataset (buildings footprints) */
  SECONDARY_DATASET: 'sf-buildings-2026',
  /** Secondary table name in DuckDB SQL */
  SECONDARY_TABLE: 'buildings',
  /** Approximate system prompt token cost in stuffing mode */
  STUFFING_PROMPT_TOKENS: 1857,
} as const;

export type PipelineConfig = typeof PIPELINE;
