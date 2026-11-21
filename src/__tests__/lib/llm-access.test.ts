import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

const { mockGetUser } = vi.hoisted(() => ({ mockGetUser: vi.fn() }));

vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn().mockResolvedValue({
    auth: { getUser: mockGetUser },
  }),
}));

import { getLlmAccess } from '@/lib/llm-access';

describe('getLlmAccess', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('returns replay without checking the user when the flag is off', async () => {
    vi.stubEnv('LIVE_LLM_ENABLED', 'false');
    mockGetUser.mockResolvedValue({ data: { user: { app_metadata: { role: 'super-admin' } } } });

    expect(await getLlmAccess()).toEqual({ mode: 'replay' });
    expect(mockGetUser).not.toHaveBeenCalled();
  });

  it('returns replay when the flag is unset', async () => {
    vi.stubEnv('LIVE_LLM_ENABLED', '');

    expect(await getLlmAccess()).toEqual({ mode: 'replay' });
  });

  it('returns replay when the flag is on and the user is not a super-admin', async () => {
    vi.stubEnv('LIVE_LLM_ENABLED', 'true');
    mockGetUser.mockResolvedValue({ data: { user: { app_metadata: { role: 'viewer' } } } });

    expect(await getLlmAccess()).toEqual({ mode: 'replay' });
  });

  it('returns live when the flag is on and the user is a super-admin', async () => {
    vi.stubEnv('LIVE_LLM_ENABLED', 'true');
    mockGetUser.mockResolvedValue({ data: { user: { app_metadata: { role: 'super-admin' } } } });

    expect(await getLlmAccess()).toEqual({ mode: 'live' });
  });

  it('returns replay when the flag is on and there is no user', async () => {
    vi.stubEnv('LIVE_LLM_ENABLED', 'true');
    mockGetUser.mockResolvedValue({ data: { user: null } });

    expect(await getLlmAccess()).toEqual({ mode: 'replay' });
  });

  it('returns replay when the auth lookup throws', async () => {
    vi.stubEnv('LIVE_LLM_ENABLED', 'true');
    vi.spyOn(console, 'error').mockImplementation(() => {});
    mockGetUser.mockRejectedValue(new Error('network down'));

    expect(await getLlmAccess()).toEqual({ mode: 'replay' });
  });
});
