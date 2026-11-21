'use client';

import { useState } from 'react';

/**
 * Streamlit dashboard panel for /spatial-eval.
 *
 * Local dev:  Iframes the Streamlit app running on NEXT_PUBLIC_STREAMLIT_URL
 *             (defaults to http://localhost:8501). Start it with:
 *               cd src/exercises/spatial-eval && uv run streamlit run app.py
 *
 * Production: Set NEXT_PUBLIC_STREAMLIT_URL to your Streamlit Community Cloud
 *             URL. The page shows a launch button instead of an iframe (avoids
 *             cross-origin framing issues with Streamlit Cloud).
 */

const STREAMLIT_URL = process.env.NEXT_PUBLIC_STREAMLIT_URL || 'http://localhost:8501';
const IS_LOCAL = STREAMLIT_URL.includes('localhost') || STREAMLIT_URL.includes('127.0.0.1');

export function StreamlitPanel() {
  const [iframeError, setIframeError] = useState(false);
  const showIframe = IS_LOCAL && !iframeError;

  return (
    <div className={`flex flex-col ${showIframe ? 'h-screen' : ''}`}>

      {/* Main content */}
      {showIframe ? (
        <iframe
          src={STREAMLIT_URL}
          className="flex-1 w-full border-0"
          title="Where do LLMs think neighborhoods are?"
          onError={() => setIframeError(true)}
        />
      ) : (
        // Production card — or local fallback if Streamlit isn't running
        <div className="flex-1 flex items-center justify-center px-4 py-8 sm:px-8">
          <div className="max-w-2xl w-full bg-white rounded-2xl shadow-sm border border-gray-200 p-8 text-center">
            <div className="text-5xl mb-4">🗺️</div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              Where do LLMs think neighborhoods are?
            </h2>
            <p className="text-gray-500 text-sm mb-4 leading-relaxed">
              A dashboard comparing where different LLMs place San Francisco
              neighborhoods, and where they don&apos;t, against reference boundaries.
            </p>

            <div className="text-left text-sm text-gray-600 leading-relaxed space-y-3 mb-6">
              <p>
                Ask an LLM where the Mission starts and ends and it will answer with a confident bounding box.
                But there is no single right answer to check it against: SF Planning, OpenStreetMap, Zillow and
                Click That Hood each draw the neighborhood differently.
              </p>
              <p>
                How exact a place needs to be depends on what it is for. Law, property, zoning and administration
                need a precise, defensible boundary. Everyday life and geographic research treat a neighborhood as
                a vague region: a recognizable core with a fuzzy edge.
              </p>
              <p>
                So this tool does two things. It scores each model against SF Planning&apos;s official boundaries,
                and it measures how much the reference sources disagree with one another. A low score where the
                references disagree means something different from a low score where everyone agrees.
              </p>
            </div>

            <a
              href={STREAMLIT_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="block mb-6 overflow-hidden rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src="/assets/spatial-eval-map.png"
                alt="Spatial Eval dashboard: a map of the Bayview neighborhood comparing five LLM bounding boxes with four reference boundary sources"
                width={1600}
                height={919}
                loading="lazy"
                className="w-full h-auto"
              />
            </a>

            <a
              href={STREAMLIT_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-6 rounded-xl transition-colors mb-4"
            >
              Launch Streamlit Dashboard ↗
            </a>

            {IS_LOCAL && iframeError && (
              <div className="mt-4 p-4 bg-amber-50 border border-amber-200 rounded-lg text-left">
                <p className="text-sm font-medium text-amber-800 mb-1">Streamlit not running</p>
                <p className="text-xs text-amber-700 font-mono">
                  cd src/exercises/spatial-eval<br />
                  uv run streamlit run app.py
                </p>
              </div>
            )}

            <div className="mt-6 grid grid-cols-3 gap-3 text-left">
              {[
                { label: 'Models', value: '5 LLMs scored' },
                { label: 'Places', value: '24 SF neighborhoods' },
                { label: 'Tiers', value: '4 tiers, iconic to vernacular' },
              ].map(({ label, value }) => (
                <div key={label} className="bg-gray-50 rounded-lg p-3">
                  <div className="text-xs text-gray-400 uppercase tracking-wide">{label}</div>
                  <div className="text-sm font-medium text-gray-800 mt-0.5">{value}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
