/**
 * Record one Scout run as a replay fixture in src/content/scout-replays.
 *
 * Runs against a LOCAL dev server with live LLM enabled. It makes real,
 * billable LLM calls. Never run it against the public deployment.
 *
 * Prerequisites:
 *   1. `.env.local` on the dev machine: LIVE_LLM_ENABLED=true plus the provider key.
 *   2. Signed in to the dev server as a super-admin. Copy the Supabase auth
 *      cookie value (name starts with sb- and ends with -auth-token, including
 *      any .0/.1 chunk suffixes) from browser DevTools and export it as
 *      SCOUT_SESSION_COOKIE. Do not commit it.
 *
 * Usage:
 *   SCOUT_SESSION_COOKIE='<cookie header value>' pnpm exec tsx scripts/record-scout-replay.ts \
 *     --id coffee-soma --title "Coffee shops in SoMa" \
 *     --query "Show coffee shops in SoMa" --cost 0.01
 *
 * Limitation: the generative route returns SQL and narrative but not result
 * features or count. The fixture gets features: [] and count: 0. Replay re-runs
 * the SQL in the browser, so the map and table are still correct. Set --cost
 * from your provider dashboard; it is informational.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { ReplayIndexSchema, ScoutReplaySchema, REPLAY_ID_PATTERN } from '../src/lib/scout-replay';

const here = path.dirname(fileURLToPath(import.meta.url));
const REPLAY_DIR = path.join(here, '..', 'src', 'content', 'scout-replays');
const INDEX_PATH = path.join(REPLAY_DIR, 'index.json');

function readArg(name: string): string {
  const i = process.argv.indexOf(`--${name}`);
  const value = i === -1 ? undefined : process.argv[i + 1];
  if (!value) throw new Error(`Missing --${name}`);
  return value;
}

async function main(): Promise<void> {
  const id = readArg('id');
  const title = readArg('title');
  const query = readArg('query');
  const cost = Number(readArg('cost'));
  if (!REPLAY_ID_PATTERN.test(id)) throw new Error(`Invalid --id: ${id}`);

  const base = process.env.SCOUT_BASE_URL ?? 'http://localhost:3000';
  const cookie = process.env.SCOUT_SESSION_COOKIE;
  if (!cookie) throw new Error('Set SCOUT_SESSION_COOKIE (see header comment)');

  const res = await fetch(`${base}/api/scout/generative-query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', cookie },
    body: JSON.stringify({ query }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(`Scout route returned ${res.status}: ${JSON.stringify(data)}`);

  const replay = ScoutReplaySchema.parse({
    id,
    title,
    query,
    sql: data.sql,
    narrative: data.reasoning ?? '',
    count: 0,
    features: [],
    model: data.model ?? 'claude-sonnet-4-6',
    recordedAt: new Date().toISOString(),
    approxCostUsd: cost,
  });

  const index = ReplayIndexSchema.parse(JSON.parse(fs.readFileSync(INDEX_PATH, 'utf-8')))
    .filter((entry) => entry.id !== id);
  index.push({ id, title, query });

  fs.writeFileSync(path.join(REPLAY_DIR, `${id}.json`), `${JSON.stringify(replay, null, 2)}\n`);
  fs.writeFileSync(INDEX_PATH, `${JSON.stringify(index, null, 2)}\n`);
  console.log(`Recorded ${id} -> src/content/scout-replays/${id}.json`);
}

main().catch((err: unknown) => {
  console.error(err instanceof Error ? err.message : err);
  process.exit(1);
});
