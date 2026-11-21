/**
 * Scout Lab — Agent vs Generative UI
 * ============================================
 * Side-by-side comparison:
 *   Left  — existing Scout agent (stuffing / RAG / agent modes)
 *   Right — new generative-query endpoint that returns SQL + LayerConfig
 *
 * Layout:
 * ┌─────────────────────────────────────────────────────┐
 * │  Scout Lab header strip                             │
 * ├──────────────────────┬──────────────────────────────┤
 * │  Left: Agent Mode    │  Right: Generative UI         │
 * │  [LabMapPanel left]  │  [LabMapPanel right]          │
 * └──────────────────────┴──────────────────────────────┘
 *         [LabPromptBar — unified mode only]
 *
 * Modes:
 *   unified — one prompt fires both maps
 *   split   — each map has its own prompt bar
 */

'use client';

import { useState } from 'react';
import LabMapPanel from './components/LabMapPanel';
import LabPromptBar from './components/LabPromptBar';
import { useAuth } from '@/contexts/AuthContext';
import { ScoutDemoPage } from './components/ScoutDemoPage';

type PromptMode = 'unified' | 'split';
type ScoutMode = 'stuffing' | 'rag' | 'agent';

export default function LabPage() {
  const [promptMode, setPromptMode] = useState<PromptMode>('unified');
  const [scoutMode, setScoutMode] = useState<ScoutMode>('agent');

  // Unified mode — shared query state
  const [unifiedQuery, setUnifiedQuery] = useState('');
  const [unifiedQueryVersion, setUnifiedQueryVersion] = useState(0);

  // Per-panel loading state for the LabPromptBar disabled logic.
  // Wired to LabMapPanel's onLoadingChange callbacks so the unified prompt bar
  // disables itself while either panel has an in-flight query.
  const [leftLoading, setLeftLoading] = useState(false);
  const [rightLoading, setRightLoading] = useState(false);

  const { isAdmin, loading } = useAuth();
  // Visitors get the split layout with recorded runs; the unified live prompt is admin-only.
  const layoutMode: PromptMode = isAdmin ? promptMode : 'split';

  // Live LLM is super-admin only (server-enforced by getLlmAccess); everyone else
  // gets recorded runs, so there is no bring-your-own-key flow here.
  const [activeProvider, setActiveProvider] = useState<'claude' | 'openai'>(
    'claude',
  );

  const handleUnifiedQuery = (text: string) => {
    setUnifiedQuery(text);
    setUnifiedQueryVersion((v) => v + 1);
  };

  const SCOUT_MODE_BADGE: Record<ScoutMode, string> = {
    stuffing: 'bg-blue-100 text-blue-800',
    rag: 'bg-emerald-100 text-emerald-800',
    agent: 'bg-violet-100 text-violet-800',
  };

  const SCOUT_MODE_DESC: Record<ScoutMode, string> = {
    stuffing: 'injects the full STAC catalog into every prompt',
    rag: 'retrieves only relevant schema chunks via embedding search',
    agent: 'runs a multi-turn tool loop to build the SQL query',
  };

  // The app is admin-only (live LLM calls). Visitors get the recorded demo and no map/DuckDB.
  if (loading) return <div className="h-[calc(100vh-64px)]" aria-busy="true" />;
  if (!isAdmin) return <ScoutDemoPage />;

  return (
    <div className="flex flex-col h-[calc(100vh-64px)]">
      {/* ------------------------------------------------------------------ */}
      {/* Header strip                                                         */}
      {/* ------------------------------------------------------------------ */}
      <div className="flex-shrink-0 bg-white border-b border-gray-200 z-10">
        {/* Top row: title + controls */}
        <div className="flex items-center justify-between px-4 py-2.5">
          <div className="flex items-center gap-2">
            <h1 className="text-sm font-semibold text-gray-900">Scout Lab</h1>
            <span className="text-gray-300">·</span>
            <span className="text-xs text-gray-400">
              Query strategy vs. visualization style
            </span>
          </div>

          <div className="flex items-center gap-2">
            {isAdmin && (
              <>
                {/* Unified / Split segmented control */}
                <div className="flex rounded-md border border-gray-200 overflow-hidden text-xs">
                  <button
                    onClick={() => setPromptMode('unified')}
                    className={`px-3 py-1 transition-colors ${
                      promptMode === 'unified'
                        ? 'bg-slate-700 text-white'
                        : 'bg-white text-gray-500 hover:bg-gray-50'
                    }`}
                  >
                    Unified
                  </button>
                  <button
                    onClick={() => setPromptMode('split')}
                    className={`px-3 py-1 transition-colors border-l border-gray-200 ${
                      promptMode === 'split'
                        ? 'bg-slate-700 text-white'
                        : 'bg-white text-gray-500 hover:bg-gray-50'
                    }`}
                  >
                    Split
                  </button>
                </div>
              </>
            )}
            {isAdmin && (
              <>
                <div className="flex items-center gap-1 text-xs">
                  <button
                    type="button"
                    onClick={() => setActiveProvider('claude')}
                    className={`px-2 py-0.5 rounded border transition-colors ${activeProvider === 'claude' ? 'border-orange-400 text-orange-700 bg-orange-50' : 'border-gray-200 text-gray-400 hover:bg-gray-50'}`}
                  >
                    Claude
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveProvider('openai')}
                    className={`px-2 py-0.5 rounded border transition-colors ${activeProvider === 'openai' ? 'border-green-500 text-green-700 bg-green-50' : 'border-gray-200 text-gray-400 hover:bg-gray-50'}`}
                  >
                    OpenAI
                  </button>
                </div>
                <span className="text-[10px] text-gray-400 font-mono px-2 py-0.5 rounded border border-gray-200 bg-gray-50">
                  env keys
                </span>
              </>
            )}
          </div>
        </div>

        {/* Explainer strip */}
        <div className="flex border-t border-gray-100">
          <div className="w-1/2 px-4 py-2 flex items-start gap-2.5 border-r border-gray-100">
            <span
              className={`mt-0.5 flex-shrink-0 text-xs font-semibold px-2 py-0.5 rounded-full ${SCOUT_MODE_BADGE[scoutMode]}`}
            >
              {scoutMode}
            </span>
            <div className="min-w-0">
              <p className="text-xs font-medium text-gray-700">
                Query strategy
              </p>
              <p className="text-[11px] text-gray-400 leading-relaxed">
                {SCOUT_MODE_DESC[scoutMode]} — switch modes to compare.
              </p>
            </div>
          </div>
          <div className="w-1/2 px-4 py-2 flex items-start gap-2.5">
            <span className="mt-0.5 flex-shrink-0 text-xs font-semibold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800">
              generative
            </span>
            <div className="min-w-0">
              <p className="text-xs font-medium text-gray-700">
                Visualization style
              </p>
              <p className="text-[11px] text-gray-400 leading-relaxed">
                Same SQL results — AI picks color, marker type, radius, and
                opacity.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Two-column map panels                                               */}
      {/* ------------------------------------------------------------------ */}
      <div className="flex-1 flex min-h-0 gap-3 p-3 bg-slate-100">
        {/* Left panel — card */}
        <div className="flex-1 flex flex-col min-h-0 rounded-xl overflow-hidden shadow-sm border border-gray-200 bg-white">
          <LabMapPanel
            side="left"
            externalQuery={layoutMode === 'unified' ? unifiedQuery : undefined}
            externalQueryVersion={
              layoutMode === 'unified' ? unifiedQueryVersion : undefined
            }
            standalone={layoutMode === 'split'}
            replayOnly={!isAdmin}
            scoutMode={scoutMode}
            onScoutModeChange={setScoutMode}
            provider={activeProvider}
            onLoadingChange={setLeftLoading}
          />
        </div>

        {/* Right panel — card */}
        <div className="flex-1 flex flex-col min-h-0 rounded-xl overflow-hidden shadow-sm border border-gray-200 bg-white">
          <LabMapPanel
            side="right"
            externalQuery={layoutMode === 'unified' ? unifiedQuery : undefined}
            externalQueryVersion={
              layoutMode === 'unified' ? unifiedQueryVersion : undefined
            }
            standalone={layoutMode === 'split'}
            replayOnly={!isAdmin}
            onLoadingChange={setRightLoading}
          />
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Unified mode prompt bar                                             */}
      {/* ------------------------------------------------------------------ */}
      {layoutMode === 'unified' && (
        <div className="flex-shrink-0 bg-slate-100 px-3 pb-3">
          <div className="max-w-4xl mx-auto bg-white rounded-xl shadow-md border border-gray-200 px-5 py-4">
            <LabPromptBar
              onQuery={handleUnifiedQuery}
              isLoading={leftLoading || rightLoading}
            />
          </div>
        </div>
      )}
    </div>
  );
}
