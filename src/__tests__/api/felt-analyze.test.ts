import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { NextRequest } from 'next/server';

vi.mock('@anthropic-ai/sdk');
vi.mock('@/lib/rate-limit', () => ({
  checkRateLimit: vi.fn().mockReturnValue(true),
}));

import Anthropic from '@anthropic-ai/sdk';
import { checkRateLimit } from '@/lib/rate-limit';
import { POST } from '@/app/api/felt-analyze/route';

function makeRequest(body: unknown): NextRequest {
  return new NextRequest('http://localhost/api/felt-analyze', {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' },
  });
}

function mockClient() {
  const create = vi.fn().mockResolvedValue({ content: [{ type: 'text', text: 'narrative' }] });
  vi.mocked(Anthropic).mockImplementation(function () {
    return { messages: { create } };
  } as unknown as typeof Anthropic);
  return create;
}

describe('POST /api/felt-analyze', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(checkRateLimit).mockReturnValue(true);
    vi.stubEnv('ANTHROPIC_API_KEY', 'sk-ant-api03-server');
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  describe('production', () => {
    beforeEach(() => vi.stubEnv('NODE_ENV', 'production'));

    it('returns 401 and never uses the server key when no apiKey is sent', async () => {
      const res = await POST(makeRequest({ prompt: 'What is TRI?' }));

      expect(res.status).toBe(401);
      expect((await res.json()).error).toMatch(/Missing API key/);
      expect(Anthropic).not.toHaveBeenCalled();
    });

    it('uses the body apiKey, not the server key', async () => {
      const create = mockClient();

      const res = await POST(makeRequest({ prompt: 'What is TRI?', apiKey: 'sk-ant-api03-byok' }));

      expect(res.status).toBe(200);
      expect((await res.json()).response).toBe('narrative');
      expect(Anthropic).toHaveBeenCalledWith({ apiKey: 'sk-ant-api03-byok' });
      expect(create).toHaveBeenCalledOnce();
    });
  });

  describe('development', () => {
    beforeEach(() => vi.stubEnv('NODE_ENV', 'development'));

    it('falls back to the server ANTHROPIC_API_KEY when no apiKey is sent', async () => {
      mockClient();

      const res = await POST(makeRequest({ prompt: 'What is TRI?' }));

      expect(res.status).toBe(200);
      expect(Anthropic).toHaveBeenCalledWith({ apiKey: 'sk-ant-api03-server' });
    });

    it('prefers the body apiKey over the server key', async () => {
      mockClient();

      await POST(makeRequest({ prompt: 'What is TRI?', apiKey: 'sk-ant-api03-byok' }));

      expect(Anthropic).toHaveBeenCalledWith({ apiKey: 'sk-ant-api03-byok' });
    });

    it('returns 401 when neither a body key nor a server key exists', async () => {
      vi.stubEnv('ANTHROPIC_API_KEY', '');

      const res = await POST(makeRequest({ prompt: 'What is TRI?' }));

      expect(res.status).toBe(401);
      expect((await res.json()).error).toMatch(/\.env\.local/);
      expect(Anthropic).not.toHaveBeenCalled();
    });
  });

  it('returns 429 when the rate limit is exceeded', async () => {
    vi.mocked(checkRateLimit).mockReturnValue(false);

    const res = await POST(makeRequest({ prompt: 'What is TRI?', apiKey: 'sk-ant-api03-byok' }));

    expect(res.status).toBe(429);
    expect(Anthropic).not.toHaveBeenCalled();
  });
});
