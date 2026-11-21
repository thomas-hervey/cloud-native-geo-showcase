/**
 * Recorded Scout runs ("replays"): shared schema and display helpers.
 * Client-safe: no Node imports. Server file access lives in scout-replay-server.ts.
 */
import { z } from 'zod';

export const REPLAY_ID_PATTERN = /^[a-z0-9][a-z0-9-]{0,63}$/;

const PlaceSchema = z.object({
  id: z.string(),
  name: z.string(),
  category: z.string(),
  lat: z.number(),
  lon: z.number(),
});

export const ScoutReplaySchema = z.object({
  id: z.string().regex(REPLAY_ID_PATTERN),
  title: z.string().min(1),
  query: z.string().min(1),
  sql: z.string().min(1),
  narrative: z.string(),
  count: z.number().int().nonnegative(),
  features: z.array(PlaceSchema),
  model: z.string().min(1),
  /** null marks a hand-written placeholder, not a real recording. */
  recordedAt: z.iso.datetime().nullable(),
  approxCostUsd: z.number().nonnegative(),
});

export const ReplayIndexSchema = z
  .array(
    z.object({
      id: z.string().regex(REPLAY_ID_PATTERN),
      title: z.string().min(1),
      query: z.string().min(1),
    })
  )
  .refine((entries) => new Set(entries.map((e) => e.id)).size === entries.length, {
    message: 'Replay ids must be unique',
  });

export type ScoutReplay = z.infer<typeof ScoutReplaySchema>;
export type ReplayIndexEntry = z.infer<typeof ReplayIndexSchema>[number];

/** Label shown above a replayed result. Placeholders are never presented as recordings. */
export function describeReplay(replay: Pick<ScoutReplay, 'model' | 'recordedAt'>): string {
  if (replay.recordedAt === null) {
    return `Sample, not a real recording · ${replay.model}`;
  }
  const date = replay.recordedAt.slice(0, 10);
  return `Recorded run · ${replay.model} · ${date}`;
}
