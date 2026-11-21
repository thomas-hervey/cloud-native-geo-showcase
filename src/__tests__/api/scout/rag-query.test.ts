import { describe, it, expect, vi, beforeEach } from 'vitest';
import { NextRequest } from 'next/server';

vi.mock('fs');
vi.mock('@anthropic-ai/sdk');
vi.mock('openai');
// Existing behaviour tests run with live LLM access; the gate itself is covered in llm-gate.test.ts.
vi.mock('@/lib/llm-access', () => ({
  getLlmAccess: vi.fn().mockResolvedValue({ mode: 'live' }),
}));

vi.mock('@/lib/rate-limit', () => ({
  checkRateLimit: vi.fn().mockReturnValue(true),
}));

import { checkRateLimit } from '@/lib/rate-limit';
import * as fs from 'fs';

const mockCheckRateLimit = vi.mocked(checkRateLimit);

// A minimal retrieval index with one schema doc
const MOCK_INDEX = {
  model: 'all-MiniLM-L6-v2',
  collection: 'scout_schema_chunks',
  exported_at: '2026-01-01T00:00:00Z',
  num_documents: 1,
  documents: [
    {
      id: 'doc-1',
      document: 'places table schema for SF coffee shops',
      metadata: {
        chunk_type: 'schema_fields',
        dataset_id: 'sf-places',
        table_name: 'places',
        row_count: 50000,
        duckdb_notes: 'Use FROM places.',
        schema_json: JSON.stringify({ name: 'Name', category: 'Category' }),
      },
      embedding: [], // empty triggers keyword fallback
    },
  ],
};

function makeRequest(body: unknown): NextRequest {
  return new NextRequest('http://localhost/api/scout/rag-query', {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' },
  });
}

function mockIndexFile() {
  vi.mocked(fs.existsSync).mockReturnValue(true);
  vi.mocked(fs.readFileSync).mockReturnValue(JSON.stringify(MOCK_INDEX));
}

// Build a mock Anthropic constructor that returns the given SQL (must use 'function' keyword)
function makeAnthropicMock(sqlOrError: string | Error) {
  return {
    default: vi.fn().mockImplementation(function () {
      return {
        messages: {
          create: vi.fn().mockImplementation(function () {
            if (sqlOrError instanceof Error) {
              return Promise.reject(sqlOrError);
            }
            return Promise.resolve({
              content: [{ type: 'text', text: sqlOrError }],
              usage: { input_tokens: 100, output_tokens: 30 },
            });
          }),
        },
      };
    }),
  };
}

const SAFE_SQL = 'LOAD spatial;\nSELECT id, name FROM places LIMIT 10;';

// Helper that imports (or re-uses cached) route module and returns POST handler
async function getHandler() {
  const mod = await import('@/app/api/scout/rag-query/route');
  return mod.POST;
}

describe('POST /api/scout/rag-query', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockCheckRateLimit.mockReturnValue(true);
    // Ensure API key is set for tests that exercise the LLM path
    process.env.ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY ?? 'test-anthropic-key';
    delete process.env.LLM_PROVIDER;
  });

  it('returns 400 when query is missing', async () => {
    const { POST } = await import('@/app/api/scout/rag-query/route');
    const res = await POST(makeRequest({}));
    expect(res.status).toBe(400);
  });

  it('returns 429 when rate limit exceeded', async () => {
    mockCheckRateLimit.mockReturnValue(false);
    const { POST } = await import('@/app/api/scout/rag-query/route');
    const res = await POST(makeRequest({ query: 'coffee' }));
    expect(res.status).toBe(429);
  });

  it('returns 503 when retrieval index not found', async () => {
    vi.mocked(fs.existsSync).mockReturnValue(false);
    const { POST } = await import('@/app/api/scout/rag-query/route');
    const res = await POST(makeRequest({ query: 'coffee' }));
    expect(res.status).toBe(503);
    const body = await res.json();
    expect(body.error).toMatch(/retrieval index not found/i);
  });

  it('returns 500 when index JSON is malformed', async () => {
    vi.mocked(fs.existsSync).mockReturnValue(true);
    vi.mocked(fs.readFileSync).mockReturnValue('not valid json {{{{');
    const { POST } = await import('@/app/api/scout/rag-query/route');
    const res = await POST(makeRequest({ query: 'coffee' }));
    expect(res.status).toBe(500);
    const body = await res.json();
    expect(body.error).toMatch(/failed to parse/i);
  });

  it('returns 422 when LLM generates unsafe SQL', async () => {
    vi.doMock('@anthropic-ai/sdk', () => makeAnthropicMock('DROP TABLE places'));
    vi.resetModules();
    mockIndexFile();
    const mod = await import('@/app/api/scout/rag-query/route');
    const res = await mod.POST(makeRequest({ query: 'drop everything' }));
    expect(res.status).toBe(422);
  });

  it('returns 200 with retrieved_chunks, filtered_chunks, and pipeline on happy path', async () => {
    vi.doMock('@anthropic-ai/sdk', () => makeAnthropicMock(SAFE_SQL));
    vi.resetModules();
    mockIndexFile();
    const mod = await import('@/app/api/scout/rag-query/route');
    const res = await mod.POST(makeRequest({ query: 'coffee shops' }));
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.sql).toBeTruthy();
    expect(Array.isArray(body.retrieved_chunks)).toBe(true);
    expect(Array.isArray(body.filtered_chunks)).toBe(true);
    expect(body.pipeline).toBeDefined();
    expect(body.pipeline.scoring_method).toBeTruthy();
  });

  it('sql in 200 response has LIMIT clause (enforceLimitClause applied)', async () => {
    const sqlNoLimit = 'LOAD spatial;\nSELECT id, name FROM places'; // no LIMIT
    vi.doMock('@anthropic-ai/sdk', () => makeAnthropicMock(sqlNoLimit));
    vi.resetModules();
    mockIndexFile();
    const mod = await import('@/app/api/scout/rag-query/route');
    const res = await mod.POST(makeRequest({ query: 'coffee shops' }));
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.sql).toMatch(/LIMIT/i);
  });

  it('returns 503 when ANTHROPIC_API_KEY is not set', async () => {
    mockIndexFile();
    const savedKey = process.env.ANTHROPIC_API_KEY;
    delete process.env.ANTHROPIC_API_KEY;
    delete process.env.LLM_PROVIDER;
    const POST = await getHandler();
    const res = await POST(makeRequest({ query: 'coffee shops' }));
    expect(res.status).toBe(503);
    const body = await res.json();
    expect(body.error).toMatch(/missing api key/i);
    if (savedKey) process.env.ANTHROPIC_API_KEY = savedKey;
  });

  it('returns 200 using OpenAI provider when LLM_PROVIDER=openai', async () => {
    const safeSql = 'SELECT id, name FROM places LIMIT 10;';
    vi.doMock('openai', () => ({
      default: vi.fn().mockImplementation(function () {
        return {
          embeddings: {
            create: vi.fn().mockResolvedValue({
              data: [{ embedding: new Array(384).fill(0.1) }],
            }),
          },
          chat: {
            completions: {
              create: vi.fn().mockResolvedValue({
                choices: [{ message: { content: safeSql } }],
                usage: { prompt_tokens: 100, completion_tokens: 30 },
              }),
            },
          },
        };
      }),
    }));
    vi.resetModules();
    // Re-mock fs after resetModules
    vi.mock('fs');
    vi.mocked(fs.existsSync).mockReturnValue(true);
    vi.mocked(fs.readFileSync).mockReturnValue(JSON.stringify(MOCK_INDEX));
    process.env.LLM_PROVIDER = 'openai';
    process.env.OPENAI_API_KEY = 'test-key';
    const mod = await import('@/app/api/scout/rag-query/route');
    const res = await mod.POST(makeRequest({ query: 'coffee shops' }));
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.provider).toBe('openai');
    delete process.env.LLM_PROVIDER;
    delete process.env.OPENAI_API_KEY;
  });
});
