import { describe, it, expect, vi, beforeEach } from 'vitest';
import { NextRequest } from 'next/server';

// ---------------------------------------------------------------------------
// Mocks — must be declared before any imports that load these modules
// ---------------------------------------------------------------------------

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

vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn().mockResolvedValue({
    auth: {
      getUser: vi.fn().mockResolvedValue({
        data: { user: { app_metadata: { role: 'super-admin' } } },
      }),
    },
  }),
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

import { checkRateLimit } from '@/lib/rate-limit';
import * as fs from 'fs';

const mockCheckRateLimit = vi.mocked(checkRateLimit);

// A minimal valid STAC item that the route expects
const MOCK_STAC_ITEM = {
  properties: {
    'scout:schema': { id: 'ID', name: 'Name', category: 'Category', lat: 'Lat', lon: 'Lon' },
    'scout:categories': ['coffee_shop', 'restaurant'],
    'scout:table_name': 'places',
    'scout:duckdb_notes': 'Use FROM places.',
    'scout:row_count': 50000,
  },
};

function makeRequest(body: unknown): NextRequest {
  return new NextRequest('http://localhost/api/scout/query', {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' },
  });
}

function mockStacFile() {
  vi.mocked(fs.readFileSync).mockReturnValue(JSON.stringify(MOCK_STAC_ITEM));
}

// Build a mock Anthropic constructor that returns the given SQL (or throws)
function makeAnthropicMock(sqlOrError: string | Error) {
  return {
    default: vi.fn().mockImplementation(function () {
      return {
        messages: {
          create: vi.fn().mockImplementation(() => {
            if (sqlOrError instanceof Error) {
              return Promise.reject(sqlOrError);
            }
            return Promise.resolve({
              content: [{ type: 'text', text: sqlOrError }],
              usage: { input_tokens: 200, output_tokens: 40 },
            });
          }),
        },
      };
    }),
  };
}

// Helper that imports (or re-uses cached) route module and returns POST handler
async function getHandler() {
  const mod = await import('@/app/api/scout/query/route');
  return mod.POST;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('POST /api/scout/query', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockCheckRateLimit.mockReturnValue(true);
    // Ensure API key is set for tests that exercise the LLM path
    process.env.ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY ?? 'test-anthropic-key';
    delete process.env.LLM_PROVIDER;
  });

  it('returns 400 when query field is missing', async () => {
    mockStacFile();
    const { POST } = await import('@/app/api/scout/query/route');
    const res = await POST(makeRequest({}));
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.error).toMatch(/query/i);
  });

  it('returns 400 when query is empty string', async () => {
    mockStacFile();
    const { POST } = await import('@/app/api/scout/query/route');
    const res = await POST(makeRequest({ query: '   ' }));
    expect(res.status).toBe(400);
  });

  it('returns 400 when body is invalid JSON', async () => {
    const { POST } = await import('@/app/api/scout/query/route');
    const req = new NextRequest('http://localhost/api/scout/query', {
      method: 'POST',
      body: 'not json',
      headers: { 'Content-Type': 'application/json' },
    });
    const res = await POST(req);
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.error).toMatch(/invalid json/i);
  });

  it('returns 429 when rate limit is exceeded', async () => {
    mockCheckRateLimit.mockReturnValue(false);
    const { POST } = await import('@/app/api/scout/query/route');
    const res = await POST(makeRequest({ query: 'coffee shops' }));
    expect(res.status).toBe(429);
  });

  it('returns 503 when STAC file is not found', async () => {
    vi.mocked(fs.readFileSync).mockImplementation(() => {
      throw new Error('ENOENT: no such file or directory');
    });
    const { POST } = await import('@/app/api/scout/query/route');
    const res = await POST(makeRequest({ query: 'coffee shops' }));
    expect(res.status).toBe(503);
    const body = await res.json();
    expect(body.error).toMatch(/STAC catalog not found/i);
  });

  it('returns 422 when LLM generates DDL', async () => {
    mockStacFile();
    vi.doMock('@anthropic-ai/sdk', () => makeAnthropicMock('DROP TABLE places'));
    vi.resetModules();
    const { POST } = await import('@/app/api/scout/query/route');
    const res = await POST(makeRequest({ query: 'delete everything' }));
    expect(res.status).toBe(422);
    const body = await res.json();
    expect(body.error).toMatch(/unsafe SQL/i);
  });

  it('returns 502 when LLM SDK throws', async () => {
    mockStacFile();
    vi.doMock('@anthropic-ai/sdk', () => makeAnthropicMock(new Error('Network timeout')));
    vi.resetModules();
    const { POST } = await import('@/app/api/scout/query/route');
    const res = await POST(makeRequest({ query: 'coffee shops' }));
    expect(res.status).toBe(502);
  });

  it('returns 200 with sql, provider, usage on happy path', async () => {
    mockStacFile();
    const safeSql = 'LOAD spatial;\nSELECT id, name FROM places LIMIT 10;';
    vi.doMock('@anthropic-ai/sdk', () => makeAnthropicMock(safeSql));
    vi.resetModules();
    const { POST } = await import('@/app/api/scout/query/route');
    const res = await POST(makeRequest({ query: 'coffee shops near Dolores Park' }));
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.sql).toBeTruthy();
    expect(body.provider).toBe('claude');
    expect(body.usage.input_tokens).toBe(200);
  });

  it('returns 503 when ANTHROPIC_API_KEY is not set', async () => {
    mockStacFile();
    const savedKey = process.env.ANTHROPIC_API_KEY;
    delete process.env.ANTHROPIC_API_KEY;
    delete process.env.LLM_PROVIDER;
    const POST = await getHandler();
    const res = await POST(makeRequest({ query: 'coffee shops' }));
    expect(res.status).toBe(503);
    const body = await res.json();
    expect(body.error).toMatch(/missing server api key/i);
    if (savedKey) process.env.ANTHROPIC_API_KEY = savedKey;
  });

  it('returns 200 using OpenAI provider when LLM_PROVIDER=openai', async () => {
    const safeSql = 'SELECT id, name FROM places LIMIT 10;';
    vi.doMock('openai', () => ({
      default: vi.fn().mockImplementation(function () {
        return {
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
    mockStacFile();
    process.env.LLM_PROVIDER = 'openai';
    process.env.OPENAI_API_KEY = 'test-key';
    const mod = await import('@/app/api/scout/query/route');
    const res = await mod.POST(makeRequest({ query: 'coffee shops' }));
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.provider).toBe('openai');
    delete process.env.LLM_PROVIDER;
    delete process.env.OPENAI_API_KEY;
  });
});
