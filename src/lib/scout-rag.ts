/**
 * Scout RAG — Pure Functions
 * ==========================
 * Extracted from rag-query/route.ts for testability.
 * No I/O, no side effects — all functions are pure.
 */

// ---------------------------------------------------------------------------
// Types (re-exported so consumers don't need to reach into the route)
// ---------------------------------------------------------------------------

export interface IndexDocument {
  id: string;
  document: string;
  metadata: Record<string, string | number | boolean | null>;
  embedding: number[];
}

export interface RetrievalIndex {
  model: string;
  collection: string;
  exported_at: string;
  num_documents: number;
  documents: IndexDocument[];
}

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

// ---------------------------------------------------------------------------
// Vector math
// ---------------------------------------------------------------------------

export function dotProduct(a: number[], b: number[]): number {
  let sum = 0;
  for (let i = 0; i < a.length; i++) sum += a[i] * b[i];
  return sum;
}

export function magnitude(v: number[]): number {
  return Math.sqrt(v.reduce((s, x) => s + x * x, 0));
}

export function cosineSimilarity(a: number[], b: number[]): number {
  const magA = magnitude(a);
  const magB = magnitude(b);
  if (magA === 0 || magB === 0) return 0;
  return dotProduct(a, b) / (magA * magB);
}

// ---------------------------------------------------------------------------
// Keyword fallback
// ---------------------------------------------------------------------------

/**
 * TF overlap score. Note: score can exceed 1.0 when the document repeats
 * query tokens (hits counts total occurrences, not unique matches).
 * e.g. keywordSimilarity("coffee", "coffee coffee") === 2.0
 */
export function keywordSimilarity(query: string, document: string): number {
  const queryTokens = new Set(query.toLowerCase().split(/\W+/).filter(Boolean));
  const docTokens = document.toLowerCase().split(/\W+/).filter(Boolean);
  let hits = 0;
  for (const token of docTokens) {
    if (queryTokens.has(token)) hits++;
  }
  return queryTokens.size > 0 ? hits / queryTokens.size : 0;
}

// ---------------------------------------------------------------------------
// Retrieval
// ---------------------------------------------------------------------------

export function retrieveTopK(
  index: RetrievalIndex,
  queryEmbedding: number[] | null,
  query: string,
  k: number,
): { doc: IndexDocument; score: number }[] {
  const scored = index.documents.map((doc) => {
    let score: number;
    if (queryEmbedding && doc.embedding.length === queryEmbedding.length) {
      score = cosineSimilarity(queryEmbedding, doc.embedding);
    } else {
      score = keywordSimilarity(query, doc.document);
    }
    return { doc, score };
  });

  return scored.sort((a, b) => b.score - a.score).slice(0, k);
}

/**
 * Splits top-K results into used (score >= simThreshold) and filtered (below).
 */
export function partitionChunks(
  topK: { doc: IndexDocument; score: number }[],
  simThreshold: number,
): {
  used: { doc: IndexDocument; score: number }[];
  filtered: FilteredChunk[];
} {
  const used: { doc: IndexDocument; score: number }[] = [];
  const filtered: FilteredChunk[] = [];

  for (const item of topK) {
    if (item.score >= simThreshold) {
      used.push(item);
    } else {
      const meta = item.doc.metadata;
      filtered.push({
        id: item.doc.id,
        chunk_type: String(meta.chunk_type ?? ''),
        dataset_id: String(meta.dataset_id ?? '?'),
        similarity: Math.round(item.score * 1000) / 1000,
        reason: `similarity ${item.score.toFixed(3)} < threshold ${simThreshold}`,
      });
    }
  }

  return { used, filtered };
}

// ---------------------------------------------------------------------------
// Prompt builder
// ---------------------------------------------------------------------------

export function buildRagPrompt(
  chunks: { doc: IndexDocument; score: number }[],
): { prompt: string; retrievedChunks: RetrievedChunk[] } {
  const tableSchemas: Record<
    string,
    { schema: Record<string, string>; rowCount: number; notes: string }
  > = {};
  const categoryBlocks: string[] = [];
  const retrieved: RetrievedChunk[] = [];

  for (const { doc, score } of chunks) {
    const meta = doc.metadata;
    const chunkType = String(meta.chunk_type ?? '');
    const datasetId = String(meta.dataset_id ?? '?');

    retrieved.push({
      id: doc.id,
      chunk_type: chunkType,
      dataset_id: datasetId,
      similarity: Math.round(score * 1000) / 1000,
      text_preview: doc.document.slice(0, 100),
    });

    if (chunkType === 'schema_fields') {
      const schema = JSON.parse(
        String(meta.schema_json ?? '{}'),
      ) as Record<string, string>;
      const table = String(meta.table_name ?? datasetId);
      const rowCount = Number(meta.row_count ?? 0);
      const notes = String(meta.duckdb_notes ?? '');
      tableSchemas[table] = { schema, rowCount, notes };
    } else if (chunkType === 'category_vocabulary') {
      const categories = JSON.parse(
        String(meta.categories_json ?? '[]'),
      ) as string[];
      const table = String(meta.table_name ?? datasetId);
      if (categories.length) {
        categoryBlocks.push(`Valid categories for ${table}: ${categories.join(', ')}`);
      }
    }
  }

  let schemaSection = '';
  for (const [table, info] of Object.entries(tableSchemas)) {
    schemaSection += `\nTable '${table}' (${info.rowCount.toLocaleString()} rows):\n`;
    for (const [col, desc] of Object.entries(info.schema)) {
      schemaSection += `  ${col.padEnd(12)} -- ${desc}\n`;
    }
    if (info.notes) schemaSection += `DuckDB notes: ${info.notes}\n`;
  }

  const categorySection =
    categoryBlocks.length > 0
      ? categoryBlocks.join('\n')
      : '(no category constraints — use name-based filtering if needed)';

  const prompt = `You are a SQL query generator for a DuckDB geospatial database.

## Retrieved Schema (semantic match for this query)
${schemaSection}

## Category constraints
${categorySection}

## Output rules
- Return ONLY a valid DuckDB SQL SELECT statement. No markdown, no explanation.
- Always include: LOAD spatial; as the first line.
- SELECT id, name, category, lat, lon at minimum (use NULL for missing cols).
- LIMIT 200 rows unless the user specifies otherwise.
- Use ST_DWithin for proximity queries (0.005 degrees ≈ 500m at SF latitude).
- Never generate INSERT, UPDATE, DELETE, DROP, or CREATE.
- If no matching category exists, use LIKE '%keyword%' on the name column.`;

  return { prompt, retrievedChunks: retrieved };
}
