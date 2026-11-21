import { z } from 'zod';

/**
 * Typed contract for src/content/spatial-eval/run-summary.json, produced by
 * src/exercises/spatial-eval/scripts/export_run_summary.py.
 */

const statsShape = {
  n: z.number().int().nonnegative(),
  nValid: z.number().int().nonnegative(),
  medianIou: z.number().nullable(),
  medianCentroidErrM: z.number().nullable(),
};

export const tierStatsSchema = z.object({ tier: z.number().int(), ...statsShape });

export const modelStatsSchema = z.object({
  modelId: z.string(),
  displayName: z.string(),
  provider: z.string().nullable().optional(),
  successorOf: z.string().nullable().optional(),
  places: z.number().int(),
  tiers: z.array(tierStatsSchema),
  ...statsShape,
});

export const periodSchema = z.object({
  id: z.string(),
  label: z.string(),
  firstRunAt: z.string(),
  lastRunAt: z.string(),
  models: z.array(modelStatsSchema),
});

export const runSummarySchema = z.object({
  generatedAt: z.string(),
  referenceSource: z.string(),
  variantId: z.string(),
  placeCount: z.number().int(),
  periods: z.array(periodSchema),
});

export type TierStats = z.infer<typeof tierStatsSchema>;
export type ModelStats = z.infer<typeof modelStatsSchema>;
export type Period = z.infer<typeof periodSchema>;
export type RunSummary = z.infer<typeof runSummarySchema>;

export interface Metrics {
  medianIou: number | null;
  medianCentroidErrM: number | null;
}

export interface ComparisonRow {
  key: string;
  label: string;
  /** Set when the current model replaces a retired baseline model. */
  successorOf: string | null;
  baseline: Metrics | null;
  current: Metrics | null;
  deltaIou: number | null;
  deltaCentroidErrM: number | null;
}

export interface RunComparison {
  baseline: Period;
  current: Period | null;
  models: ComparisonRow[];
  /** One entry per tier, each with a row per model. */
  tiers: { tier: number; rows: ComparisonRow[] }[];
}

function delta(a: number | null | undefined, b: number | null | undefined): number | null {
  return a == null || b == null ? null : b - a;
}

function toMetrics(s: Metrics | undefined): Metrics | null {
  return s ? { medianIou: s.medianIou, medianCentroidErrM: s.medianCentroidErrM } : null;
}

function row(
  key: string,
  label: string,
  successorOf: string | null,
  baseline: Metrics | null,
  current: Metrics | null,
): ComparisonRow {
  return {
    key,
    label,
    successorOf,
    baseline,
    current,
    deltaIou: delta(baseline?.medianIou, current?.medianIou),
    deltaCentroidErrM: delta(baseline?.medianCentroidErrM, current?.medianCentroidErrM),
  };
}

/**
 * Pair models across two periods. A current model pairs with the baseline
 * model of the same id, or with the one it is the `successorOf`. Baseline
 * models with no counterpart keep a row with `current: null`.
 */
function pairModels(baseline: Period, current: Period | null): [ModelStats | undefined, ModelStats | undefined][] {
  const pairs: [ModelStats | undefined, ModelStats | undefined][] = [];
  const used = new Set<string>();
  for (const b of baseline.models) {
    const c = current?.models.find((m) => m.modelId === b.modelId || m.successorOf === b.modelId);
    if (c) used.add(c.modelId);
    pairs.push([b, c]);
  }
  for (const c of current?.models ?? []) {
    if (!used.has(c.modelId)) pairs.push([undefined, c]);
  }
  return pairs;
}

export function buildRunComparison(summary: RunSummary, currentId?: string): RunComparison | null {
  const [baseline, ...rest] = summary.periods;
  if (!baseline) return null;
  const current = (currentId ? rest.find((p) => p.id === currentId) : rest.at(-1)) ?? null;
  const pairs = pairModels(baseline, current);

  const label = (b?: ModelStats, c?: ModelStats) => (c ?? b)?.displayName ?? '';
  const key = (b?: ModelStats, c?: ModelStats) => `${b?.modelId ?? '-'}|${c?.modelId ?? '-'}`;
  const successor = (b?: ModelStats, c?: ModelStats) =>
    c && b && c.modelId !== b.modelId ? b.displayName : (c?.successorOf ?? null);

  const models = pairs.map(([b, c]) => row(key(b, c), label(b, c), successor(b, c), toMetrics(b), toMetrics(c)));

  const tierIds = [...new Set(pairs.flatMap(([b, c]) => [...(b?.tiers ?? []), ...(c?.tiers ?? [])].map((t) => t.tier)))]
    .sort((x, y) => x - y);
  const tiers = tierIds.map((tier) => ({
    tier,
    rows: pairs.map(([b, c]) =>
      row(
        key(b, c),
        label(b, c),
        successor(b, c),
        toMetrics(b?.tiers.find((t) => t.tier === tier)),
        toMetrics(c?.tiers.find((t) => t.tier === tier)),
      ),
    ),
  }));

  return { baseline, current, models, tiers };
}
