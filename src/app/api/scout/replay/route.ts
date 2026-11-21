/**
 * GET /api/scout/replay?id=<id>
 * Returns one recorded Scout run from src/content/scout-replays. No LLM call.
 * Public: see PUBLIC_API_ROUTES in src/lib/supabase/middleware.ts.
 */
import { NextRequest, NextResponse } from 'next/server';
import { REPLAY_ID_PATTERN } from '@/lib/scout-replay';
import { loadReplay } from '@/lib/scout-replay-server';

export async function GET(request: NextRequest) {
  const id = request.nextUrl.searchParams.get('id');
  if (!id || !REPLAY_ID_PATTERN.test(id)) {
    return NextResponse.json({ error: 'Invalid replay id' }, { status: 400 });
  }

  const replay = await loadReplay(id);
  if (!replay) {
    return NextResponse.json({ error: 'Unknown replay id' }, { status: 404 });
  }

  return NextResponse.json(replay, {
    headers: { 'Cache-Control': 'public, max-age=3600' },
  });
}
