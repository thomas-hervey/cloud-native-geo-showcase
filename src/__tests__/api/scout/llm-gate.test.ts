import { describe, it, expect, vi, beforeEach } from 'vitest';
import { NextRequest } from 'next/server';

vi.mock('fs');
vi.mock('@anthropic-ai/sdk');
vi.mock('openai');
vi.mock('@/lib/rate-limit', () => ({
  checkRateLimit: vi.fn().mockReturnValue(true),
}));
vi.mock('@/lib/llm-access', () => ({
  getLlmAccess: vi.fn().mockResolvedValue({ mode: 'replay' }),
}));

import Anthropic from '@anthropic-ai/sdk';
import { POST as scoutQuery } from '@/app/api/scout/query/route';
import { POST as generativeQuery } from '@/app/api/scout/generative-query/route';
import { POST as ragQuery } from '@/app/api/scout/rag-query/route';
import { POST as agentQuery } from '@/app/api/scout/agent-query/route';

const ROUTES = [
  ['scout/query', scoutQuery],
  ['scout/generative-query', generativeQuery],
  ['scout/rag-query', ragQuery],
  ['scout/agent-query', agentQuery],
] as const;

function makeRequest(path: string): NextRequest {
  return new NextRequest(`http://localhost/api/${path}`, {
    method: 'POST',
    body: JSON.stringify({ query: 'coffee shops in SoMa', apiKey: 'sk-ant-api03-byok' }),
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('Scout LLM routes in replay mode', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.ANTHROPIC_API_KEY = 'sk-ant-api03-server';
  });

  it.each(ROUTES)('returns 403 live_llm_disabled from %s without constructing an LLM client', async (path, POST) => {
    const res = await POST(makeRequest(path));

    expect(res.status).toBe(403);
    expect(await res.json()).toEqual({ error: 'live_llm_disabled', mode: 'replay' });
    expect(Anthropic).not.toHaveBeenCalled();
  });
});
