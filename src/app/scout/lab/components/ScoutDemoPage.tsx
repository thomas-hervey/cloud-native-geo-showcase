import Link from 'next/link';

const DEMO_VIDEO = '/assets/scout-lab-demo.mp4';
const DEMO_POSTER = '/assets/scout-lab-demo-poster.jpg';

const MODES = [
  {
    name: 'Stuffing',
    text: 'puts the full dataset catalog into every prompt. Simple, but costly and noisy as the catalog grows.',
  },
  {
    name: 'RAG',
    text: 'retrieves only the schema chunks relevant to the question, using embedding search.',
  },
  {
    name: 'Agent',
    text: 'runs a multi-turn tool loop that searches datasets, writes SQL, runs it and checks the result.',
  },
] as const;

/**
 * What visitors see at /scout/lab. Scout makes live LLM calls, so the app itself is
 * admin-only; everyone else gets the recorded walkthrough and an explanation.
 * Deliberately renders no map, no DuckDB and no query UI.
 */
export function ScoutDemoPage() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm sm:p-8">
        <p className="mb-2 inline-block rounded-full bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700">
          Coming soon · admin-only for now
        </p>
        <h1 className="text-2xl font-semibold text-gray-900">Scout Lab</h1>
        <p className="mt-2 text-gray-600">
          Scout turns a plain-English question about places into a map. It is a
          test bench for one question: how well do LLMs reason about geography,
          and which product patterns around them actually help?
        </p>

        <video
          src={DEMO_VIDEO}
          poster={DEMO_POSTER}
          aria-label="Recorded Scout Lab session: asking for parks in the Marina District, then comparing the agent's query strategy with the generative map styling"
          autoPlay
          muted
          loop
          playsInline
          controls
          preload="auto"
          className="mt-6 h-auto w-full rounded-lg border border-gray-200 bg-black"
        />

        <div className="mt-8 grid gap-8 md:grid-cols-2">
          <section>
            <h2 className="text-base font-semibold text-gray-900">
              Three ways to answer the question
            </h2>
            <p className="mt-1 text-sm text-gray-600">
              The same natural-language geospatial query is translated into SQL
              three ways, then run on the map so the results can be compared.
            </p>
            <ul className="mt-3 space-y-2 text-sm text-gray-700">
              {MODES.map(({ name, text }) => (
                <li key={name}>
                  <span className="font-medium text-gray-900">{name}</span>{' '}
                  {text}
                </li>
              ))}
            </ul>
          </section>

          <section>
            <h2 className="text-base font-semibold text-gray-900">
              A styling agent
            </h2>
            <p className="mt-1 text-sm text-gray-700">
              A second model looks at the results and decides how to draw them:
              color, marker type, radius and opacity, with its reasoning shown.
              Parks come back green, coffee shops brown. The right-hand map in
              the video is this agent at work.
            </p>
            <h2 className="mt-5 text-base font-semibold text-gray-900">
              Why it exists
            </h2>
            <p className="mt-1 text-sm text-gray-700">
              To measure how reliably each mode handles geospatial reasoning,
              and to try out product applications like automatic styling.
              Because every query calls an LLM, live access is limited to admins
              while that spend is protected.
            </p>
          </section>
        </div>

        <div className="mt-8 flex flex-wrap items-center gap-4 border-t border-gray-100 pt-5 text-sm">
          <Link
            href="/spatial-eval"
            className="font-medium text-blue-700 hover:underline"
          >
            See the related LLM spatial evaluation →
          </Link>
          <Link
            href="/login?redirect_to=/scout/lab"
            className="text-gray-500 hover:underline"
          >
            Admin sign in
          </Link>
        </div>
      </div>
    </div>
  );
}
