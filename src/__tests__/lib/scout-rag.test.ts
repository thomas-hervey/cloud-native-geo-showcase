import { describe, it, expect } from 'vitest';
import {
  cosineSimilarity,
  keywordSimilarity,
  retrieveTopK,
  partitionChunks,
  buildRagPrompt,
  type IndexDocument,
  type RetrievalIndex,
} from '@/lib/scout-rag';

// ---------------------------------------------------------------------------
// cosineSimilarity
// ---------------------------------------------------------------------------

describe('cosineSimilarity', () => {
  it('returns 1.0 for identical vectors', () => {
    expect(cosineSimilarity([1, 0, 0], [1, 0, 0])).toBeCloseTo(1.0);
  });

  it('returns 0.0 for orthogonal vectors', () => {
    expect(cosineSimilarity([1, 0, 0], [0, 1, 0])).toBeCloseTo(0.0);
  });

  it('returns 0.0 when first vector is zero (no divide-by-zero)', () => {
    expect(cosineSimilarity([0, 0, 0], [1, 2, 3])).toBe(0);
  });

  it('returns 0.0 when second vector is zero', () => {
    expect(cosineSimilarity([1, 2, 3], [0, 0, 0])).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// keywordSimilarity
// ---------------------------------------------------------------------------

describe('keywordSimilarity', () => {
  it('returns 1.0 when all query tokens match', () => {
    expect(keywordSimilarity('coffee', 'coffee')).toBe(1.0);
  });

  it('returns 0.0 when no tokens match', () => {
    expect(keywordSimilarity('coffee', 'pizza')).toBe(0.0);
  });

  it('returns fractional score for partial match', () => {
    // query tokens: {"coffee", "shop"}, doc tokens: ["coffee"]
    // hits = 1, queryTokens.size = 2 → score = 0.5
    expect(keywordSimilarity('coffee shop', 'coffee')).toBe(0.5);
  });

  it('can return scores > 1.0 when doc repeats query tokens (documented contract)', () => {
    // query tokens: {"coffee"}, doc tokens: ["coffee", "coffee"]
    // hits = 2, queryTokens.size = 1 → score = 2.0
    expect(keywordSimilarity('coffee', 'coffee coffee')).toBe(2.0);
  });
});

// ---------------------------------------------------------------------------
// Helpers for building test fixtures
// ---------------------------------------------------------------------------

function makeDoc(
  id: string,
  text: string,
  embedding: number[] = [],
  meta: Record<string, string | number | boolean | null> = {},
): IndexDocument {
  return { id, document: text, metadata: meta, embedding };
}

function makeIndex(docs: IndexDocument[]): RetrievalIndex {
  return {
    model: 'test-model',
    collection: 'test',
    exported_at: '2026-01-01',
    num_documents: docs.length,
    documents: docs,
  };
}

// ---------------------------------------------------------------------------
// retrieveTopK
// ---------------------------------------------------------------------------

describe('retrieveTopK', () => {
  it('returns exactly k results sorted by score descending (cosine path)', () => {
    const docs = [
      makeDoc('a', 'coffee shop', [0, 1]),  // cosine with [0,1] = 1.0
      makeDoc('b', 'pizza place', [1, 0]),  // cosine with [0,1] = 0.0
      makeDoc('c', 'bar',         [0.5, 0.5]), // cosine ≈ 0.707
    ];
    const index = makeIndex(docs);
    const query_emb = [0, 1];
    const results = retrieveTopK(index, query_emb, 'coffee', 2);
    expect(results).toHaveLength(2);
    expect(results[0].doc.id).toBe('a'); // highest cosine
    expect(results[1].doc.id).toBe('c');
  });

  it('falls back to keyword scoring when embedding dimensions differ', () => {
    // queryEmbedding has dim 3, docs have dim 2 → falls back to keyword
    const docs = [
      makeDoc('a', 'coffee shop', [0, 1]),
      makeDoc('b', 'pizza pizza', [1, 0]),
    ];
    const index = makeIndex(docs);
    const query_emb = [0, 1, 0]; // dim mismatch → keyword fallback
    const results = retrieveTopK(index, query_emb, 'coffee', 2);
    expect(results[0].doc.id).toBe('a'); // "coffee shop" matches "coffee"
  });

  it('falls back to keyword scoring when queryEmbedding is null', () => {
    const docs = [
      makeDoc('a', 'park'),
      makeDoc('b', 'coffee shop'),
    ];
    const index = makeIndex(docs);
    const results = retrieveTopK(index, null, 'coffee', 2);
    expect(results[0].doc.id).toBe('b'); // "coffee shop" scores higher for "coffee" query
  });
});

// ---------------------------------------------------------------------------
// partitionChunks
// ---------------------------------------------------------------------------

describe('partitionChunks', () => {
  it('puts chunks at/above threshold into used', () => {
    const chunks = [
      { doc: makeDoc('a', 'schema'), score: 0.8 },
      { doc: makeDoc('b', 'schema'), score: 0.05 }, // exactly at threshold
    ];
    const { used, filtered } = partitionChunks(chunks, 0.05);
    expect(used).toHaveLength(2);
    expect(filtered).toHaveLength(0);
  });

  it('puts chunks below threshold into filtered with reason string', () => {
    const chunks = [{ doc: makeDoc('a', 'schema', [], { dataset_id: 'ds1', chunk_type: 'schema_fields' }), score: 0.01 }];
    const { used, filtered } = partitionChunks(chunks, 0.05);
    expect(used).toHaveLength(0);
    expect(filtered).toHaveLength(1);
    expect(filtered[0].reason).toContain('< threshold');
    expect(filtered[0].dataset_id).toBe('ds1');
  });

  it('handles empty input gracefully', () => {
    const { used, filtered } = partitionChunks([], 0.05);
    expect(used).toHaveLength(0);
    expect(filtered).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// buildRagPrompt
// ---------------------------------------------------------------------------

describe('buildRagPrompt', () => {
  it('builds schema section from schema_fields chunk', () => {
    const schemaJson = JSON.stringify({ name: 'Place name', category: 'Place category' });
    const doc = makeDoc('a', 'schema text', [], {
      chunk_type: 'schema_fields',
      dataset_id: 'sf-places',
      table_name: 'places',
      row_count: 100000,
      duckdb_notes: 'Use ABS(lat - y) < 0.005',
      schema_json: schemaJson,
    });
    const { prompt, retrievedChunks } = buildRagPrompt([{ doc, score: 0.9 }]);
    expect(prompt).toContain("Table 'places'");
    expect(prompt).toContain('Place name');
    expect(prompt).toContain('Use ABS(lat - y) < 0.005');
    expect(retrievedChunks).toHaveLength(1);
    expect(retrievedChunks[0].chunk_type).toBe('schema_fields');
  });

  it('builds category section from category_vocabulary chunk', () => {
    const categoriesJson = JSON.stringify(['coffee_shop', 'restaurant', 'bar']);
    const doc = makeDoc('b', 'category text', [], {
      chunk_type: 'category_vocabulary',
      dataset_id: 'sf-places',
      table_name: 'places',
      categories_json: categoriesJson,
    });
    const { prompt } = buildRagPrompt([{ doc, score: 0.7 }]);
    expect(prompt).toContain('coffee_shop');
    expect(prompt).toContain('restaurant');
  });

  it('shows fallback text when no category chunk is present', () => {
    const { prompt } = buildRagPrompt([]);
    expect(prompt).toContain('no category constraints');
  });
});
