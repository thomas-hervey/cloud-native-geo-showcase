/**
 * Scout Shared Types
 * ==================
 * Single source of truth for interfaces shared between:
 *   - src/app/scout/page.tsx
 *   - src/app/scout/components/ChatBar.tsx, PipelineModal.tsx
 *   - src/app/scout/lab/ (Module 31 Lab components)
 *   - src/app/api/scout/generative-query/route.ts
 *
 * Previously these were duplicated across page.tsx and ChatBar.tsx.
 */

// ---------------------------------------------------------------------------
// Map result types (shared by ScoutMap and LabMap)
// ---------------------------------------------------------------------------

export interface PlaceResult {
  id: string;
  name: string;
  category: string;
  lat: number;
  lon: number;
}

export interface QueryResult {
  count: number;
  features: PlaceResult[];
}

// ---------------------------------------------------------------------------
// Scout mode (shared by page.tsx and PipelineModal.tsx)
// ---------------------------------------------------------------------------

export type Mode = 'stuffing' | 'rag' | 'agent';

// ---------------------------------------------------------------------------
// RAG types
// ---------------------------------------------------------------------------

export interface RetrievedChunk {
  id: string;
  chunk_type: string;
  dataset_id: string;
  similarity: number;
  text_preview: string;
}

export interface FilteredChunk {
  id: string;
  chunk_type: string;
  dataset_id: string;
  similarity: number;
  reason: string;
}

export interface Pipeline {
  scoring_method: string;
  top_k_fetched: number;
  sim_threshold: number;
  chunks_used: number;
  chunks_filtered: number;
  index_model: string;
  index_exported_at: string;
}

// ---------------------------------------------------------------------------
// Agent types
// ---------------------------------------------------------------------------

export interface ToolCall {
  step: number;
  tool: string;
  input: Record<string, unknown>;
  output: string;
  elapsed_ms: number;
}

export interface AgentUsage {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
}

// ---------------------------------------------------------------------------
// Module 31: Generative UI layer config
// ---------------------------------------------------------------------------

/**
 * LayerConfig — the visualization specification the LLM returns alongside SQL.
 *
 * The LLM chooses values based on the semantic intent of the query:
 *   - color: intuitive RGB (green for parks, orange for restaurants, blue for water)
 *   - type: 'circle' for point data, 'heatmap' for density queries
 *   - radius: 6–12 depending on expected result density
 *   - opacity: 0.7–0.9
 *   - label: human-readable description of the style choice
 */
export interface LayerConfig {
  type: 'circle' | 'heatmap';
  color: [number, number, number]; // RGB 0-255
  radius: number;                  // pixels
  opacity: number;                 // 0.0–1.0
  label?: string;                  // e.g. "warm orange — restaurants"
}
