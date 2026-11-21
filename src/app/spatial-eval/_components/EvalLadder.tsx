const LEVELS = [
  {
    level: 'L1',
    name: 'Geometry identification',
    status: 'Done',
    color: 'text-blue-600',
    question: 'Where is the Mission? Give a bounding box.',
    scored: 'Overlap (IoU) and centroid error against reference polygons.',
    tests: 'Whether the model knows where places are.',
  },
  {
    level: 'L2',
    name: 'Topology relations',
    status: 'Built, runs pending',
    color: 'text-orange-600',
    question: 'Which neighborhoods border the Mission?',
    scored:
      'Overlap between the model’s neighbor list and the one derived from the official polygons (ST_Touches), plus DE-9IM relations.',
    tests:
      'Whether the model knows how places relate, without being handed coordinates.',
  },
  {
    level: 'L3',
    name: 'Symbolic rules',
    status: 'Planned',
    color: 'text-green-600',
    question:
      'Which of these places are north of Market Street, or within 500 m of a BART station?',
    scored: 'Exact geometric computation on the reference data.',
    tests:
      'Whether the model applies a stated spatial rule, or pattern-matches on names.',
  },
  {
    level: 'L4',
    name: 'Causal prediction',
    status: 'Planned',
    color: 'text-purple-600',
    question:
      'If the Bay Bridge closes, or sea level rises one metre, which neighborhoods are affected first?',
    scored: 'A simple GIS simulation (network, elevation) as the baseline.',
    tests:
      'Whether the model can reason about spatial processes, not only static layouts.',
  },
  {
    level: 'L5',
    name: 'Planning',
    status: 'Planned',
    color: 'text-red-600',
    question:
      'Site a clinic that serves the most people within 15 minutes, avoiding flood zones.',
    scored: 'Constraint satisfaction and a solver baseline.',
    tests:
      'Whether the model can plan toward a goal across several spatial steps, with tools.',
  },
] as const;

export function EvalLadder() {
  return (
    <section className="mx-auto w-full max-w-4xl rounded-2xl border border-gray-200 bg-white p-6 shadow-sm sm:p-8">
      <h2 className="text-lg font-semibold text-gray-900">
        Where this goes next
      </h2>
      <p className="mt-1 mb-5 text-sm leading-relaxed text-gray-500">
        Everything above is level 1: does the model know where a place is? Each
        later level asks for more than recall, and each is scored against
        something computed, not a model’s opinion. Level 1 comes first because
        every later level depends on it.
      </p>
      <ol className="space-y-4">
        {LEVELS.map((l) => (
          <li
            key={l.level}
            className="grid gap-1 border-t border-gray-100 pt-4 first:border-t-0 first:pt-0 sm:grid-cols-[9rem_1fr] sm:gap-4"
          >
            <div>
              <div className={`text-sm font-semibold ${l.color}`}>
                {l.level} · {l.name}
              </div>
              <div className="text-xs text-gray-400">{l.status}</div>
            </div>
            <dl className="space-y-1 text-sm text-gray-600">
              <div>
                <dt className="inline font-medium text-gray-800">Ask: </dt>
                <dd className="inline">{l.question}</dd>
              </div>
              <div>
                <dt className="inline font-medium text-gray-800">
                  Scored by:{' '}
                </dt>
                <dd className="inline">{l.scored}</dd>
              </div>
              <div>
                <dt className="inline font-medium text-gray-800">Tests: </dt>
                <dd className="inline">{l.tests}</dd>
              </div>
            </dl>
          </li>
        ))}
      </ol>
    </section>
  );
}
