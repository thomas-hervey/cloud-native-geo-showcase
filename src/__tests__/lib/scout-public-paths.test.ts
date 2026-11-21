import { describe, it, expect, vi, afterEach } from 'vitest';
import { isPublicPath } from '@/lib/supabase/middleware';

describe('isPublicPath for Scout replay', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('makes the replay API public', () => {
    expect(isPublicPath('/api/scout/replay')).toBe(true);
  });

  it('keeps the live Scout API routes protected', () => {
    expect(isPublicPath('/api/scout/query')).toBe(false);
    expect(isPublicPath('/api/scout/generative-query')).toBe(false);
  });

  it('keeps the Scout lab page public whether or not live LLM is on', () => {
    vi.stubEnv('LIVE_LLM_ENABLED', 'false');
    expect(isPublicPath('/scout/lab')).toBe(true);
    vi.stubEnv('LIVE_LLM_ENABLED', 'true');
    expect(isPublicPath('/scout/lab')).toBe(true);
  });

  it('does not open other lab paths', () => {
    vi.stubEnv('LIVE_LLM_ENABLED', 'false');
    expect(isPublicPath('/scout/lab/anything')).toBe(false);
  });

  it('makes the roadmap and the /scout redirect public', () => {
    expect(isPublicPath('/roadmap')).toBe(true);
    expect(isPublicPath('/scout')).toBe(true);
  });

  it('serves static media and the maplibre worker without a session', () => {
    expect(isPublicPath('/assets/scout-lab-demo.mp4')).toBe(true);
    expect(isPublicPath('/maplibre/maplibre-gl-worker.mjs')).toBe(true);
  });

  it('keeps resources gated', () => {
    expect(isPublicPath('/resources')).toBe(false);
  });
});
