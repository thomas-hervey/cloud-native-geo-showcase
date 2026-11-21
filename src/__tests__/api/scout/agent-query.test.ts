import { describe, it, expect, vi, beforeEach } from 'vitest';
import { NextRequest } from 'next/server';

// ---------------------------------------------------------------------------
// Mocks — must be declared before any imports that load these modules
// ---------------------------------------------------------------------------

// Mock fs so loadIndex() doesn't hit the real filesystem.
// existsSync returns false → loadIndex() throws, toolSearchDatasets catches
// and returns { error: ... } without crashing the agent loop.
vi.mock('fs');

vi.mock('@anthropic-ai/sdk');

// Existing behaviour tests run with live LLM access; the gate itself is covered in llm-gate.test.ts.
vi.mock('@/lib/llm-access', () => ({
  getLlmAccess: vi.fn().mockResolvedValue({ mode: 'live' }),
}));

vi.mock('@/lib/rate-limit', () => ({
  checkRateLimit: vi.fn().mockReturnValue(true),
}));

// buildDatasetSystemPromptSection is called inside buildSystemPrompt() on every
// agent turn — mock it to avoid real fs access in the server lib.
vi.mock('@/lib/scout-datasets-server', () => ({
  buildDatasetSystemPromptSection: vi.fn().mockReturnValue('## Available datasets\nplaces table available.'),
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

import { checkRateLimit } from '@/lib/rate-limit';

const mockCheckRateLimit = vi.mocked(checkRateLimit);

// Helper that imports (or re-uses cached) route module and returns POST handler
async function getHandler() {
  const mod = await import('@/app/api/scout/agent-query/route');
  return mod.POST;
}

function makeRequest(body: unknown): NextRequest {
  return new NextRequest('http://localhost/api/scout/agent-query', {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' },
  });
}

// Build a mock Anthropic constructor that returns the given response
function makeAnthropicMock(
  responseOrError:
    | { stop_reason: string; content: unknown[]; usage: { input_tokens: number; output_tokens: number } }
    | Error
) {
  return {
    default: vi.fn().mockImplementation(function () {
      return {
        messages: {
          create: vi.fn().mockImplementation(() => {
            if (responseOrError instanceof Error) {
              return Promise.reject(responseOrError);
            }
            return Promise.resolve(responseOrError);
          }),
        },
      };
    }),
  };
}

// Build a mock tool_use response
function mockToolUseResponse(
  toolName: string,
  toolInput: Record<string, unknown>,
  toolId = 'tool_1'
) {
  return {
    stop_reason: 'tool_use',
    content: [{ type: 'tool_use', id: toolId, name: toolName, input: toolInput }],
    usage: { input_tokens: 50, output_tokens: 20 },
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('POST /api/scout/agent-query', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockCheckRateLimit.mockReturnValue(true);
    // Ensure API key is set for tests that exercise the LLM path
    process.env.ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY ?? 'test-anthropic-key';
  });

  it('returns 400 when query is missing', async () => {
    const { POST } = await import('@/app/api/scout/agent-query/route');
    const res = await POST(makeRequest({}));
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.error).toMatch(/query/i);
  });

  it('returns 400 when query is empty string', async () => {
    const { POST } = await import('@/app/api/scout/agent-query/route');
    const res = await POST(makeRequest({ query: '   ' }));
    expect(res.status).toBe(400);
  });

  it('returns 429 when rate limit is exceeded', async () => {
    mockCheckRateLimit.mockReturnValue(false);
    const { POST } = await import('@/app/api/scout/agent-query/route');
    const res = await POST(makeRequest({ query: 'coffee shops' }));
    expect(res.status).toBe(429);
  });

  it('returns 200 with clarification_needed when agent calls ask_clarification', async () => {
    vi.doMock('@anthropic-ai/sdk', () =>
      makeAnthropicMock(mockToolUseResponse('ask_clarification', { question: 'Which neighborhood?' }))
    );
    vi.resetModules();
    const { POST } = await import('@/app/api/scout/agent-query/route');
    const res = await POST(makeRequest({ query: 'show me things' }));
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.clarification_needed).toBe('Which neighborhood?');
  });

  it('returns 200 with sql when agent calls execute_sql (browser-side sentinel)', async () => {
    const AGENT_SQL = 'LOAD spatial;\nSELECT id, name FROM places LIMIT 10;';
    vi.doMock('@anthropic-ai/sdk', () =>
      makeAnthropicMock(mockToolUseResponse('execute_sql', { sql: AGENT_SQL }))
    );
    vi.resetModules();
    const { POST } = await import('@/app/api/scout/agent-query/route');
    const res = await POST(makeRequest({ query: 'coffee shops' }));
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.sql).toBeTruthy();
    expect(typeof body.sql).toBe('string');
  });

  it('returns 503 when ANTHROPIC_API_KEY is not set', async () => {
    const savedKey = process.env.ANTHROPIC_API_KEY;
    delete process.env.ANTHROPIC_API_KEY;
    const POST = await getHandler();
    const res = await POST(makeRequest({ query: 'coffee shops' }));
    expect(res.status).toBe(503);
    const body = await res.json();
    expect(body.error).toMatch(/missing api key/i);
    if (savedKey) process.env.ANTHROPIC_API_KEY = savedKey;
  });

  it('returns 502 when agent loop throws', async () => {
    vi.doMock('@anthropic-ai/sdk', () =>
      makeAnthropicMock(new Error('API overloaded'))
    );
    vi.resetModules();
    const { POST } = await import('@/app/api/scout/agent-query/route');
    const res = await POST(makeRequest({ query: 'coffee shops' }));
    expect(res.status).toBe(502);
    const body = await res.json();
    expect(body.error).toBe('Agent loop failed');
    expect(body.details).toMatch(/API overloaded/i);
  });
});
