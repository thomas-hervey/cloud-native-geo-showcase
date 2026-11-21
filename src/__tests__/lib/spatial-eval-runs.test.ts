import { describe, expect, it } from 'vitest';
import summaryJson from '@/content/spatial-eval/run-summary.json';
import { buildRunComparison, runSummarySchema, type ModelStats, type Period, type RunSummary } from '@/lib/spatial-eval-runs';

function model(modelId: string, medianIou: number, medianCentroidErrM: number, extra: Partial<ModelStats> = {}): ModelStats {
  return {
    modelId,
    displayName: modelId.toUpperCase(),
    places: 2,
    n: 6,
    nValid: 6,
    medianIou,
    medianCentroidErrM,
    tiers: [{ tier: 1, n: 3, nValid: 3, medianIou, medianCentroidErrM }],
    ...extra,
  };
}

function period(id: string, models: ModelStats[]): Period {
  return { id, label: id, firstRunAt: `${id}-01`, lastRunAt: `${id}-01`, models };
}

function summary(periods: Period[]): RunSummary {
  return { generatedAt: '2026-11-11T00:00:00Z', referenceSource: 'sf_planning', variantId: 'baseline_v2', placeCount: 2, periods };
}

describe('buildRunComparison', () => {
  it('returns null when there are no periods', () => {
    expect(buildRunComparison(summary([]))).toBeNull();
  });

  it('shows baseline only when there is a single period', () => {
    const result = buildRunComparison(summary([period('2026-03', [model('a', 0.4, 300)])]));
    expect(result?.current).toBeNull();
    expect(result?.models[0]).toMatchObject({ baseline: { medianIou: 0.4 }, current: null, deltaIou: null });
  });

  it('pairs same model ids and computes deltas', () => {
    const result = buildRunComparison(
      summary([period('2026-03', [model('a', 0.4, 300)]), period('2026-11', [model('a', 0.5, 250)])]),
    );
    const row = result?.models[0];
    expect(row?.deltaIou).toBeCloseTo(0.1);
    expect(row?.deltaCentroidErrM).toBe(-50);
    expect(row?.successorOf).toBeNull();
    expect(result?.tiers[0].rows[0].deltaIou).toBeCloseTo(0.1);
  });

  it('pairs a successor with the retired baseline model', () => {
    const result = buildRunComparison(
      summary([
        period('2026-03', [model('old', 0.3, 400)]),
        period('2026-11', [model('new', 0.6, 200, { successorOf: 'old' })]),
      ]),
    );
    expect(result?.models).toHaveLength(1);
    expect(result?.models[0]).toMatchObject({ label: 'NEW', successorOf: 'OLD', deltaCentroidErrM: -200 });
  });

  it('keeps unmatched models from either period', () => {
    const result = buildRunComparison(
      summary([period('2026-03', [model('a', 0.4, 300)]), period('2026-11', [model('b', 0.5, 250)])]),
    );
    expect(result?.models.map((r) => [r.baseline !== null, r.current !== null])).toEqual([
      [true, false],
      [false, true],
    ]);
  });
});

describe('run-summary.json', () => {
  it('matches the schema', () => {
    expect(() => runSummarySchema.parse(summaryJson)).not.toThrow();
  });
});
