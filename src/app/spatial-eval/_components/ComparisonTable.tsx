import type { ComparisonRow, Metrics } from '@/lib/spatial-eval-runs';

type MetricKey = keyof Metrics;

const FORMAT: Record<MetricKey, (v: number) => string> = {
  medianIou: (v) => v.toFixed(3),
  medianCentroidErrM: (v) => `${Math.round(v)} m`,
};

/** Higher IoU is better; lower centroid error is better. */
const HIGHER_IS_BETTER: Record<MetricKey, boolean> = {
  medianIou: true,
  medianCentroidErrM: false,
};

function Value({ value, metric }: { value: number | null | undefined; metric: MetricKey }) {
  return <>{value == null ? '—' : FORMAT[metric](value)}</>;
}

function Delta({ value, metric }: { value: number | null; metric: MetricKey }) {
  if (value == null) return <span className="text-gray-300">—</span>;
  const better = HIGHER_IS_BETTER[metric] ? value > 0 : value < 0;
  const color = value === 0 ? 'text-gray-500' : better ? 'text-emerald-700' : 'text-rose-700';
  const sign = value > 0 ? '+' : value < 0 ? '−' : '±';
  return <span className={color}>{sign}{FORMAT[metric](Math.abs(value))}</span>;
}

interface ComparisonTableProps {
  rows: ComparisonRow[];
  baselineLabel: string;
  currentLabel: string | null;
}

export function ComparisonTable({ rows, baselineLabel, currentLabel }: ComparisonTableProps) {
  const metrics: { key: MetricKey; label: string; deltaKey: 'deltaIou' | 'deltaCentroidErrM' }[] = [
    { key: 'medianIou', label: 'Median IoU', deltaKey: 'deltaIou' },
    { key: 'medianCentroidErrM', label: 'Median centroid error', deltaKey: 'deltaCentroidErrM' },
  ];

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm text-left">
        <thead className="text-xs text-gray-500 uppercase tracking-wide">
          <tr className="border-b border-gray-200">
            <th rowSpan={2} className="py-2 pr-4 font-medium">Model</th>
            {metrics.map((m) => (
              <th key={m.key} colSpan={currentLabel ? 3 : 1} className="py-2 px-2 font-medium text-center">
                {m.label}
              </th>
            ))}
          </tr>
          <tr className="border-b border-gray-200">
            {metrics.map((m) => (
              <MetricSubheads key={m.key} baselineLabel={baselineLabel} currentLabel={currentLabel} />
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.key} className="border-b border-gray-100 last:border-0">
              <td className="py-2 pr-4 text-gray-900">
                {r.label}
                {r.successorOf && (
                  <span className="block text-xs text-gray-400">successor to {r.successorOf}</span>
                )}
              </td>
              {metrics.map((m) => (
                <MetricCells key={m.key} row={r} metric={m.key} deltaKey={m.deltaKey} showCurrent={currentLabel !== null} />
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MetricSubheads({ baselineLabel, currentLabel }: { baselineLabel: string; currentLabel: string | null }) {
  return (
    <>
      <th className="py-1 px-2 font-normal text-right">{baselineLabel}</th>
      {currentLabel && (
        <>
          <th className="py-1 px-2 font-normal text-right">{currentLabel}</th>
          <th className="py-1 px-2 font-normal text-right">Δ</th>
        </>
      )}
    </>
  );
}

interface MetricCellsProps {
  row: ComparisonRow;
  metric: MetricKey;
  deltaKey: 'deltaIou' | 'deltaCentroidErrM';
  showCurrent: boolean;
}

function MetricCells({ row, metric, deltaKey, showCurrent }: MetricCellsProps) {
  return (
    <>
      <td className="py-2 px-2 text-right tabular-nums text-gray-700">
        <Value value={row.baseline?.[metric]} metric={metric} />
      </td>
      {showCurrent && (
        <>
          <td className="py-2 px-2 text-right tabular-nums text-gray-700">
            <Value value={row.current?.[metric]} metric={metric} />
          </td>
          <td className="py-2 px-2 text-right tabular-nums">
            <Delta value={row[deltaKey]} metric={metric} />
          </td>
        </>
      )}
    </>
  );
}
