import type { RunComparison } from '@/lib/spatial-eval-runs';
import { ComparisonTable } from './ComparisonTable';

const TIER_LABELS: Record<number, string> = {
  1: 'Tier 1 · famous, well defined',
  2: 'Tier 2 · common, moderately vague',
  3: 'Tier 3 · local knowledge',
  4: 'Tier 4 · hyper-local vernacular',
};

interface RunComparisonSectionProps {
  comparison: RunComparison;
  referenceSource: string;
  placeCount: number;
}

export function RunComparisonSection({ comparison, referenceSource, placeCount }: RunComparisonSectionProps) {
  const { baseline, current } = comparison;
  const title = current ? `${baseline.label} vs. ${current.label}` : `${baseline.label} baseline`;

  return (
    <section className="max-w-4xl w-full mx-auto bg-white rounded-2xl shadow-sm border border-gray-200 p-6 sm:p-8">
      <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
      <p className="text-sm text-gray-500 mt-1 mb-4 leading-relaxed">
        Medians across {placeCount} neighborhoods × 3 runs, bounding-box answers scored against{' '}
        <code className="text-xs">{referenceSource}</code>. Higher IoU is better; lower centroid error is better.
      </p>

      {!current && (
        <p className="text-sm bg-amber-50 border border-amber-200 text-amber-800 rounded-lg p-3 mb-4">
          No later run has been recorded yet. Once a tagged re-run is exported, this table shows both
          periods side by side with deltas.
        </p>
      )}

      <ComparisonTable rows={comparison.models} baselineLabel={baseline.label} currentLabel={current?.label ?? null} />

      <details className="mt-6">
        <summary className="cursor-pointer text-sm font-medium text-gray-700">By place tier</summary>
        <div className="mt-4 space-y-6">
          {comparison.tiers.map(({ tier, rows }) => (
            <div key={tier}>
              <h3 className="text-sm font-medium text-gray-800 mb-2">{TIER_LABELS[tier] ?? `Tier ${tier}`}</h3>
              <ComparisonTable rows={rows} baselineLabel={baseline.label} currentLabel={current?.label ?? null} />
            </div>
          ))}
        </div>
      </details>
    </section>
  );
}
