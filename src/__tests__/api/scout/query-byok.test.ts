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

const mockGetUser = vi.fn();
vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn().mockResolvedValue({
    auth: { getUser: mockGetUser },
  }),
}));

import * as fs from 'fs';

const MOCK_STAC = {
  properties: {
    'scout:schema': { id: 'ID', name: 'Name', category: 'Cat', lat: 'Lat', lon: 'Lon' },
    'scout:categories': ['coffee_shop'],
    'scout:table_name': 'places',
    'scout:duckdb_notes': '',
    'scout:row_count': 100,
  },
};

function mockStac() {
  vi.mocked(fs.readFileSync).mockReturnValue(JSON.stringify(MOCK_STAC));
}

function makeAnthropicMock(sql: string) {
  return {
    default: vi.fn().mockImplementation(function () {
      return {
        messages: {
          create: vi.fn().mockResolvedValue({
            content: [{ type: 'text', text: sql }],
            usage: { input_tokens: 10, output_tokens: 5 },
          }),
        },
      };
    }),
  };
}

function makeRequest(body: unknown): NextRequest {
  return new NextRequest('http://localhost/api/scout/query', {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('Scout query route — BYOK', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockStac();
  });

  it('returns 503 when no apiKey provided and user is not admin', async () => {
    mockGetUser.mockResolvedValue({ data: { user: { app_metadata: { role: 'viewer' } } } });
    process.env.ANTHROPIC_API_KEY = '';

    vi.resetModules();
    const { POST } = await import('@/app/api/scout/query/route');
    const res = await POST(makeRequest({ query: 'coffee shops' }));
    expect(res.status).toBe(503);
    const body = await res.json();
    expect(body.error).toMatch(/api key required/i);
  });

  it('uses env var key when user is super-admin (ignores any supplied apiKey)', async () => {
    mockGetUser.mockResolvedValue({
      data: { user: { app_metadata: { role: 'super-admin' } } },
    });
    process.env.ANTHROPIC_API_KEY = 'sk-ant-api03-envkey';

    vi.resetModules();
    vi.doMock('@anthropic-ai/sdk', () => makeAnthropicMock('SELECT 1'));
    const { POST } = await import('@/app/api/scout/query/route');
    const res = await POST(makeRequest({ query: 'coffee shops', apiKey: 'sk-should-be-ignored' }));
    expect(res.status).toBe(200);
  });

  it('returns 400 when key prefix conflicts with declared provider', async () => {
    mockGetUser.mockResolvedValue({ data: { user: { app_metadata: {} } } });

    vi.resetModules();
    const { POST } = await import('@/app/api/scout/query/route');
    const res = await POST(makeRequest({
      query: 'coffee shops',
      apiKey: 'sk-ant-api03-anthropic-key',
      provider: 'openai',
    }));
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.error).toMatch(/prefix does not match/i);
  });

  it('uses provided BYOK key when user is not admin', async () => {
    mockGetUser.mockResolvedValue({ data: { user: { app_metadata: {} } } });

    vi.resetModules();
    vi.doMock('@anthropic-ai/sdk', () => makeAnthropicMock('SELECT id FROM places LIMIT 10'));
    const { POST } = await import('@/app/api/scout/query/route');
    const res = await POST(makeRequest({
      query: 'coffee shops',
      apiKey: 'sk-ant-api03-guestkey',
      provider: 'claude',
    }));
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.sql).toContain('SELECT');
  });
});
