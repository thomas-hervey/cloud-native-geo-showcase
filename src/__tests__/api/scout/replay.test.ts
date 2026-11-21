import { describe, it, expect } from 'vitest';
import { NextRequest } from 'next/server';
import { GET } from '@/app/api/scout/replay/route';

function get(query: string): Promise<Response> {
  return GET(new NextRequest(`http://localhost/api/scout/replay${query}`));
}

describe('GET /api/scout/replay', () => {
  it('returns the recorded run for a known id', async () => {
    const res = await get('?id=sample-sf-coffee');
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.id).toBe('sample-sf-coffee');
    expect(body.recordedAt).toBeNull();
  });

  it('returns 400 when id is missing', async () => {
    expect((await get('')).status).toBe(400);
  });

  it.each(['../package', '..%2Fpackage', 'a%2Fb', 'SAMPLE', '.env'])('returns 400 for unsafe id %s', async (id) => {
    expect((await get(`?id=${id}`)).status).toBe(400);
  });

  it('returns 404 for a well-formed id that is not in the index', async () => {
    expect((await get('?id=not-recorded')).status).toBe(404);
  });
});
