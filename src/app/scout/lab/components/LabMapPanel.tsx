/**
 * LabMapPanel — Self-contained Scout Lab panel
 * ==========================================================
 * Each panel owns its own map instance, DuckDB connection, and API call.
 * The two panels (left = Scout agent, right = Generative UI) are fully
 * independent — one error does not affect the other.
 *
 * Left panel:  calls existing Scout endpoints (stuffing/rag/agent)
 * Right panel: calls /api/scout/generative-query, shows LayerConfigInspector
 *
 * Both panels respond to `externalQuery` (unified mode) or show their own
 * prompt input (`standalone=true` / split mode).
 */

'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import LabMap, { type QueryResult } from './LabMap';
import LayerConfigInspector from './LayerConfigInspector';
import { DEFAULT_LAYER_CONFIG } from '@/lib/scout-layer-config';
import type { LayerConfig, ToolCall, RetrievedChunk, FilteredChunk, Pipeline, AgentUsage, PlaceResult } from '@/lib/scout-types';
import { BASE_QUERIES, AGENT_EXTRA_QUERIES, RAG_EXTRA_QUERIES } from '@/lib/scout-queries';
import PipelineModal from './PipelineModal';
import RecordedRunExamples from './RecordedRunExamples';
import { ScoutReplaySchema, describeReplay, type ScoutReplay } from '@/lib/scout-replay';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface LabMapPanelProps {
  side: 'left' | 'right';
  // Unified mode: parent drives query externally
  externalQuery?: string;
  externalQueryVersion?: number; // increment to re-trigger same query text
  // Split mode: panel owns its own prompt (show when standalone=true)
  standalone?: boolean;
  // Visitors without live access: show recorded runs from the start instead of waiting for a 403
  replayOnly?: boolean;
  // For left panel: which Scout mode (stuffing/rag/agent)
  scoutMode?: 'stuffing' | 'rag' | 'agent';
  onScoutModeChange?: (mode: 'stuffing' | 'rag' | 'agent') => void;
  apiKey?: string | null;
  provider?: 'claude' | 'openai';
  // Notifies parent when a query starts/completes so the unified LabPromptBar
  // can disable itself while either panel is in-flight.
  onLoadingChange?: (isLoading: boolean) => void;
}

type ScoutMode = 'stuffing' | 'rag' | 'agent';

const SCOUT_ENDPOINT: Record<ScoutMode, string> = {
  stuffing: '/api/scout/query',
  rag: '/api/scout/rag-query',
  agent: '/api/scout/agent-query',
};

const MODE_ORDER: ScoutMode[] = ['stuffing', 'rag', 'agent'];

const MODE_BADGE: Record<ScoutMode, string> = {
  stuffing: 'bg-blue-100 text-blue-800',
  rag: 'bg-emerald-100 text-emerald-800',
  agent: 'bg-violet-100 text-violet-800',
};

const MODE_LABEL: Record<ScoutMode, string> = {
  stuffing: 'Stuffing',
  rag: 'RAG',
  agent: 'Agent',
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function LabMapPanel({
  side,
  externalQuery,
  externalQueryVersion,
  standalone = false,
  replayOnly = false,
  scoutMode = 'agent',
  onScoutModeChange,
  apiKey,
  provider = 'claude',
  onLoadingChange,
}: LabMapPanelProps) {
  const [executeQuery, setExecuteQuery] = useState<
    ((sql: string) => Promise<QueryResult>) | null
  >(null);

  // Query state
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resultCount, setResultCount] = useState<number | null>(null);
  const [sql, setSql] = useState('');

  // Right panel — generative state
  const [layerConfig, setLayerConfig] = useState<LayerConfig | undefined>(undefined);
  const [reasoning, setReasoning] = useState('');

  // Left panel — agent/rag trace state
  const [reasoningTrace, setReasoningTrace] = useState<ToolCall[]>([]);
  const [agentUsage, setAgentUsage] = useState<AgentUsage | null>(null);
  const [retrievedChunks, setRetrievedChunks] = useState<RetrievedChunk[]>([]);
  const [filteredChunks, setFilteredChunks] = useState<FilteredChunk[]>([]);
  const [pipeline, setPipeline] = useState<Pipeline | null>(null);

  // Results for inspection table
  const [results, setResults] = useState<PlaceResult[]>([]);

  // Replay mode: set when the live route answers live_llm_disabled
  const [liveDisabled, setLiveDisabled] = useState(false);
  const replay = liveDisabled || replayOnly;
  const [recordedRun, setRecordedRun] = useState<ScoutReplay | null>(null);

  // Standalone mode prompt
  const [localQuery, setLocalQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  // Track the last version we processed to avoid re-firing the same query
  const lastVersionRef = useRef<number>(-1);

  // -----------------------------------------------------------------------
  // Fire the query for this panel
  // -----------------------------------------------------------------------
  const fireQuery = useCallback(
    async (queryText: string) => {
      if (!executeQuery) return;
      setIsLoading(true);
      onLoadingChange?.(true);
      setError(null);
      setResultCount(null);
      setSql('');
      setLayerConfig(undefined);
      setReasoning('');
      setReasoningTrace([]);
      setAgentUsage(null);
      setRetrievedChunks([]);
      setFilteredChunks([]);
      setPipeline(null);
      setResults([]);
      setRecordedRun(null);

      try {
        let finalSql = '';
        let newLayerConfig: LayerConfig | undefined;
        let newReasoning = '';

        if (side === 'right') {
          // --- Generative query ---
          const res = await fetch('/api/scout/generative-query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: queryText }),
          });
          const data = await res.json();
          if (res.status === 403 && data.error === 'live_llm_disabled') {
            setLiveDisabled(true);
            return;
          }
          if (!res.ok) throw new Error(data.error ?? `API error: ${res.status}`);

          finalSql = data.sql ?? '';
          newLayerConfig = data.layer_config ?? DEFAULT_LAYER_CONFIG;
          newReasoning = data.reasoning ?? '';

          setLayerConfig(newLayerConfig);
          setReasoning(newReasoning);
          setSql(finalSql);
          setReasoningTrace(data.reasoning_trace ?? []);
        } else {
          // --- Scout query (stuffing/rag/agent) ---
          const endpoint = SCOUT_ENDPOINT[scoutMode];
          const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(
              scoutMode === 'stuffing'
                ? { query: queryText, ...(apiKey ? { apiKey } : {}), ...(provider ? { provider } : {}) }
                : { query: queryText }
            ),
          });
          const data = await res.json();
          if (res.status === 403 && data.error === 'live_llm_disabled') {
            setLiveDisabled(true);
            return;
          }
          if (!res.ok) throw new Error(data.error ?? `API error: ${res.status}`);

          finalSql = data.sql ?? '';
          setSql(finalSql);

          if (scoutMode === 'agent') {
            setReasoningTrace(data.reasoning_trace ?? []);
            setAgentUsage(data.usage ?? null);
          } else if (scoutMode === 'rag') {
            setRetrievedChunks(data.retrieved_chunks ?? []);
            setFilteredChunks(data.filtered_chunks ?? []);
            setPipeline(data.pipeline ?? null);
          }
        }

        if (!finalSql) {
          setError('No SQL generated');
          return;
        }

        const { count, features } = await executeQuery(finalSql);
        setResultCount(count);
        setResults(features);
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        setError(message);
      } finally {
        setIsLoading(false);
        onLoadingChange?.(false);
      }
    },
    [executeQuery, side, scoutMode, apiKey, provider, onLoadingChange]
  );

  // -----------------------------------------------------------------------
  // Play a recorded run: same map and result path as a live query
  // -----------------------------------------------------------------------
  const playRecordedRun = useCallback(
    async (id: string) => {
      if (!executeQuery) return;
      setIsLoading(true);
      onLoadingChange?.(true);
      setError(null);
      setResultCount(null);
      setResults([]);
      setRecordedRun(null);
      setSql('');

      try {
        const res = await fetch(`/api/scout/replay?id=${encodeURIComponent(id)}`);
        if (!res.ok) throw new Error(`Recorded run unavailable (${res.status})`);
        const replay = ScoutReplaySchema.parse(await res.json());

        setSql(replay.sql);
        setRecordedRun(replay);
        const { count, features } = await executeQuery(replay.sql);
        setResultCount(count);
        setResults(features);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setIsLoading(false);
        onLoadingChange?.(false);
      }
    },
    [executeQuery, onLoadingChange]
  );

  // -----------------------------------------------------------------------
  // Respond to external query (unified mode)
  // -----------------------------------------------------------------------
  useEffect(() => {
    if (
      externalQuery &&
      externalQueryVersion !== undefined &&
      externalQueryVersion !== lastVersionRef.current &&
      executeQuery !== null  // don't advance version until map engine is ready
    ) {
      lastVersionRef.current = externalQueryVersion;
      fireQuery(externalQuery);
    }
  }, [externalQuery, externalQueryVersion, fireQuery, executeQuery]);

  // -----------------------------------------------------------------------
  // Standalone submit
  // -----------------------------------------------------------------------
  const handleStandaloneSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = localQuery.trim();
    if (!trimmed || isLoading) return;
    fireQuery(trimmed);
  };

  const exampleQueries =
    side === 'left' && scoutMode === 'agent'
      ? [...BASE_QUERIES, ...AGENT_EXTRA_QUERIES]
      : side === 'left' && scoutMode === 'rag'
      ? [...BASE_QUERIES, ...RAG_EXTRA_QUERIES]
      : [...BASE_QUERIES];

  const nextMode = MODE_ORDER[(MODE_ORDER.indexOf(scoutMode) + 1) % MODE_ORDER.length];

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------
  const accentBorder =
    side === 'left'
      ? scoutMode === 'agent' ? 'border-t-violet-400'
        : scoutMode === 'rag' ? 'border-t-emerald-400'
        : 'border-t-blue-400'
      : 'border-t-amber-400';

  return (
    <div className="flex flex-col h-full">
      {/* Map area — flex-1 */}
      <div className="flex-1 relative min-h-0">
        <LabMap
          onReady={(execFn) => setExecuteQuery(() => execFn)}
          layerConfig={side === 'right' ? layerConfig : undefined}
        />
      </div>

      {/* Bottom info panel — white bg, colored top accent, generous padding */}
      <div
        className={`bg-white border-t-2 ${accentBorder} overflow-y-auto`}
        style={{ maxHeight: '42vh' }}
      >
        <div className="px-5 py-4 space-y-3">
          {/* Header row */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {side === 'left' ? (
                <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full ${MODE_BADGE[scoutMode]}`}>
                  {MODE_LABEL[scoutMode]} mode
                </span>
              ) : (
                <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-800">
                  Generative UI
                </span>
              )}
            </div>

            {/* Left panel: pipeline diagram trigger + mode cycle toggle */}
            {side === 'left' && (
              <div className="flex items-center gap-2">
                <PipelineModal mode={scoutMode} />
                {onScoutModeChange && (
                  <button
                    onClick={() => onScoutModeChange(nextMode)}
                    title={`Switch to ${nextMode} mode`}
                    className="text-xs px-2 py-0.5 rounded-full border border-gray-200 text-gray-500 hover:bg-gray-50 transition-colors"
                  >
                    → {nextMode}
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Standalone prompt bar */}
          {standalone && (
            <form onSubmit={handleStandaloneSubmit} className="flex gap-2">
              <input
                ref={inputRef}
                type="text"
                value={localQuery}
                onChange={(e) => setLocalQuery(e.target.value)}
                placeholder={
                  side === 'right'
                    ? 'Generative query...'
                    : `Scout (${scoutMode})...`
                }
                disabled={isLoading || replay}
                className="flex-1 px-3 py-1.5 border border-gray-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-slate-300 disabled:bg-gray-50"
              />
              <button
                type="submit"
                disabled={isLoading || !localQuery.trim()}
                className={`px-4 py-1.5 rounded-lg text-xs font-medium text-white transition-colors disabled:opacity-40 ${
                  side === 'right'
                    ? 'bg-amber-600 hover:bg-amber-700'
                    : 'bg-slate-700 hover:bg-slate-800'
                }`}
              >
                {isLoading ? '...' : 'Go'}
              </button>
            </form>
          )}

          {/* Replay mode: live LLM is off for this visitor */}
          {standalone && replay && (
            <div className="space-y-2">
              <p className="text-xs text-gray-500">
                {side === 'left' ? 'Live queries are off on this site. Pick a recorded run below.' : 'Live queries are off on this site. Recorded runs play from the left panel.'}
              </p>
              {side === 'left' && (
                <RecordedRunExamples onSelect={playRecordedRun} disabled={isLoading} />
              )}
            </div>
          )}

          {/* Example chips — standalone mode only, live mode only */}
          {standalone && !replay && (
            <div className="flex flex-wrap gap-1.5">
              {exampleQueries.slice(0, 5).map((q) => (
                <button
                  key={q}
                  onClick={() => { setLocalQuery(q); inputRef.current?.focus(); }}
                  disabled={isLoading}
                  className="text-[11px] px-2 py-0.5 rounded-full bg-gray-50 text-gray-500 hover:bg-gray-100 hover:text-gray-700 border border-gray-200 transition-colors disabled:opacity-50 truncate max-w-[140px]"
                  title={q}
                >
                  {q}
                </button>
              ))}
            </div>
          )}

          {/* Loading indicator */}
          {isLoading && (
            <div className="flex items-center gap-2 text-xs text-gray-400">
              <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              {side === 'right' ? 'Generating visualization...' : 'Querying...'}
            </div>
          )}

          {/* Error state */}
          {error && (
            <p className="text-xs text-red-500 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          {/* Recorded run label */}
          {recordedRun && (
            <p className="text-xs font-medium text-slate-600 bg-slate-100 rounded-lg px-3 py-1.5">
              {describeReplay(recordedRun)}: {recordedRun.title}
            </p>
          )}

          {/* Result count */}
          {!error && resultCount !== null && (
            <p className={`text-sm font-semibold ${side === 'right' ? 'text-amber-700' : 'text-slate-700'}`}>
              {resultCount.toLocaleString()} results
            </p>
          )}

          {/* Right panel: LayerConfigInspector */}
          {side === 'right' && layerConfig && (
            <LayerConfigInspector layerConfig={layerConfig} reasoning={reasoning} />
          )}

          {/* Right panel: Reasoning trace (tool calls from generative-query) */}
          {side === 'right' && reasoningTrace.length > 0 && (
            <details>
              <summary className="cursor-pointer text-xs text-amber-600 hover:text-amber-800">
                Reasoning trace: {reasoningTrace.length} tool call{reasoningTrace.length !== 1 ? 's' : ''}
              </summary>
              <div className="mt-1 space-y-1">
                {reasoningTrace.map((call) => (
                  <details key={call.step} className="rounded border border-amber-100 bg-white text-xs">
                    <summary className="cursor-pointer flex items-center gap-2 px-2 py-1">
                      <span className="flex-shrink-0 inline-flex items-center justify-center h-4 w-4 rounded-full bg-amber-200 text-amber-800 font-mono text-[10px]">
                        {call.step}
                      </span>
                      <span className="font-mono font-medium text-amber-900">{call.tool}</span>
                      <span className="text-gray-400 text-[10px]">{call.elapsed_ms}ms</span>
                    </summary>
                    <pre className="px-3 pb-2 text-[10px] font-mono text-gray-600 whitespace-pre-wrap">
                      {JSON.stringify(call.input, null, 2).slice(0, 400)}
                    </pre>
                  </details>
                ))}
              </div>
            </details>
          )}

          {/* Left panel: Agent reasoning trace */}
          {side === 'left' && scoutMode === 'agent' && reasoningTrace.length > 0 && (
            <details>
              <summary className="cursor-pointer text-xs font-medium text-violet-700 hover:text-violet-900">
                Reasoning trace: {reasoningTrace.length} tool call{reasoningTrace.length !== 1 ? 's' : ''}
                {agentUsage && (
                  <span className="ml-2 font-normal text-gray-400">
                    ({agentUsage.total_tokens.toLocaleString()} total tokens)
                  </span>
                )}
              </summary>
              <div className="mt-1 space-y-1">
                {reasoningTrace.map((call) => (
                  <details key={call.step} className="rounded border border-violet-100 bg-violet-50 text-xs">
                    <summary className="cursor-pointer flex items-center gap-2 px-2 py-1.5">
                      <span className="flex-shrink-0 inline-flex items-center justify-center h-4 w-4 rounded-full bg-violet-200 text-violet-800 font-mono text-[10px]">
                        {call.step}
                      </span>
                      <span className="font-medium text-violet-900 font-mono">{call.tool}</span>
                      <span className="text-gray-400 text-[10px]">{call.elapsed_ms}ms</span>
                      <span className="text-gray-500 truncate flex-1 text-[10px]">
                        {Object.values(call.input)[0] ? String(Object.values(call.input)[0]).slice(0, 50) : ''}
                      </span>
                    </summary>
                    <pre className="px-3 pb-2 text-[10px] font-mono text-gray-600 whitespace-pre-wrap">
                      {JSON.stringify(call.input, null, 2).slice(0, 400)}
                    </pre>
                  </details>
                ))}
              </div>
              {agentUsage && (
                <div className="mt-1 flex gap-3 text-[10px] text-gray-400 font-mono px-1">
                  <span>↑ {agentUsage.input_tokens.toLocaleString()} in</span>
                  <span>↓ {agentUsage.output_tokens.toLocaleString()} out</span>
                  <span>Σ {agentUsage.total_tokens.toLocaleString()} total</span>
                </div>
              )}
            </details>
          )}

          {/* Left panel: RAG retrieved chunks */}
          {side === 'left' && scoutMode === 'rag' && retrievedChunks.length > 0 && (
            <details>
              <summary className="cursor-pointer text-xs font-medium text-emerald-700 hover:text-emerald-900">
                Used in prompt: {retrievedChunks.length} chunk{retrievedChunks.length !== 1 ? 's' : ''}
                {pipeline && (
                  <span className="ml-1 font-normal text-gray-400">
                    (sim ≥ {pipeline.sim_threshold})
                  </span>
                )}
              </summary>
              <div className="mt-1 space-y-1">
                {retrievedChunks.map((chunk) => (
                  <div key={chunk.id} className="flex items-start gap-2 p-1.5 bg-emerald-50 rounded border border-emerald-100 text-xs">
                    <span className="flex-shrink-0 inline-block px-1 py-0.5 bg-emerald-200 text-emerald-800 rounded font-mono text-[10px]">
                      {chunk.similarity.toFixed(3)}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-emerald-900 text-[10px]">{chunk.dataset_id}</div>
                      <div className="text-gray-500 truncate text-[10px]">{chunk.text_preview}</div>
                    </div>
                  </div>
                ))}
              </div>
            </details>
          )}

          {/* Left panel: RAG filtered chunks */}
          {side === 'left' && scoutMode === 'rag' && filteredChunks.length > 0 && (
            <details>
              <summary className="cursor-pointer text-xs text-amber-600 hover:text-amber-800">
                Filtered: {filteredChunks.length} chunk{filteredChunks.length !== 1 ? 's' : ''} below threshold
              </summary>
              <div className="mt-1 space-y-1">
                {filteredChunks.map((chunk) => (
                  <div key={chunk.id} className="flex items-start gap-2 p-1.5 bg-amber-50 rounded border border-amber-100 text-xs">
                    <span className="flex-shrink-0 inline-block px-1 py-0.5 bg-amber-200 text-amber-800 rounded font-mono text-[10px]">
                      {chunk.similarity.toFixed(3)}
                    </span>
                    <div className="flex-1 min-w-0 text-[10px] text-gray-400 italic">{chunk.reason}</div>
                  </div>
                ))}
              </div>
            </details>
          )}

          {/* Results inspection table */}
          {results.length > 0 && (
            <details>
              <summary className="cursor-pointer text-gray-400 hover:text-gray-600 text-xs">
                Inspect results ({results.length} rows)
              </summary>
              <div className="mt-1 max-h-40 overflow-auto border border-gray-200 rounded">
                <table className="w-full text-xs font-mono">
                  <thead className="bg-gray-100 sticky top-0">
                    <tr>
                      <th className="px-2 py-1 text-left">#</th>
                      <th className="px-2 py-1 text-left">name</th>
                      <th className="px-2 py-1 text-left">category</th>
                      <th className="px-2 py-1 text-right">lon</th>
                      <th className="px-2 py-1 text-right">lat</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.slice(0, 50).map((r, i) => (
                      <tr key={i} className="border-t border-gray-100 hover:bg-blue-50">
                        <td className="px-2 py-0.5 text-gray-400">{i + 1}</td>
                        <td className="px-2 py-0.5">{r.name}</td>
                        <td className="px-2 py-0.5 text-gray-500">{r.category}</td>
                        <td className="px-2 py-0.5 text-right">{r.lon.toFixed(6)}</td>
                        <td className="px-2 py-0.5 text-right">{r.lat.toFixed(6)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {results.length > 50 && (
                  <p className="text-[10px] text-gray-400 p-2">Showing first 50 of {results.length}</p>
                )}
              </div>
            </details>
          )}

          {/* SQL — collapsed by default */}
          {sql && (
            <details>
              <summary className="cursor-pointer text-gray-400 hover:text-gray-600 text-xs">
                Show generated SQL
              </summary>
              <pre className="mt-1 p-2 bg-white/70 rounded text-[10px] overflow-x-auto whitespace-pre-wrap font-mono text-gray-700 border border-gray-200">
                {sql}
              </pre>
            </details>
          )}
        </div>
      </div>
    </div>
  );
}
