import fs from 'fs/promises';
import path from 'path';
import indexJson from '@/content/scout-replays/index.json';
import { ReplayIndexSchema, ScoutReplaySchema, type ScoutReplay } from '@/lib/scout-replay';

const REPLAY_DIR = path.join(process.cwd(), 'src', 'content', 'scout-replays');

/**
 * Loads one recorded run. The id must be an entry in index.json; the file path
 * is built only from that matched entry, so arbitrary ids cannot traverse paths.
 */
export async function loadReplay(id: string): Promise<ScoutReplay | null> {
  const index = ReplayIndexSchema.parse(indexJson);
  const entry = index.find((e) => e.id === id);
  if (!entry) return null;

  const raw = await fs.readFile(path.join(REPLAY_DIR, `${entry.id}.json`), 'utf-8');
  return ScoutReplaySchema.parse(JSON.parse(raw));
}
