/**
 * PipelineDiagram — renders a Mermaid sequence diagram for the Scout pipeline.
 * ==============================================================================
 * Client component: uses the `mermaid` npm package to convert the diagram
 * string (generated from live PIPELINE constants) into an SVG.
 *
 * Props:
 *   mode — 'stuffing' | 'rag' | 'agent'
 *     Selects the appropriate diagram. Switches automatically when the Scout
 *     page toggles between modes.
 */

'use client';

import { useEffect, useRef, useState } from 'react';
import { buildStuffingDiagram, buildRagDiagram, buildAgentDiagram } from '@/lib/scout-diagrams';
import { PIPELINE } from '@/lib/scout-pipeline';

interface PipelineDiagramProps {
    mode: 'stuffing' | 'rag' | 'agent';
}

// Stable IDs for mermaid render targets
let diagramCounter = 0;

export default function PipelineDiagram({ mode }: PipelineDiagramProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const [error, setError] = useState<string | null>(null);
    const [isRendering, setIsRendering] = useState(true);
    const idRef = useRef<string>(`scout-diagram-${++diagramCounter}`);

    const diagramText = mode === 'agent' ? buildAgentDiagram() : mode === 'rag' ? buildRagDiagram() : buildStuffingDiagram();

    useEffect(() => {
        let cancelled = false;

        async function render() {
            if (!containerRef.current) return;
            setIsRendering(true);
            setError(null);

            try {
                // Dynamic import — mermaid is large (~2MB), only load when the panel opens
                const mermaid = (await import('mermaid')).default;

                mermaid.initialize({
                    startOnLoad: false,
                    theme: 'base',
                    themeVariables: {
                        background: '#ffffff',
                        primaryColor: mode === 'agent' ? '#ede9fe' : mode === 'rag' ? '#d1fae5' : '#dbeafe',
                        primaryTextColor: '#1f2937',
                        primaryBorderColor: mode === 'agent' ? '#c4b5fd' : mode === 'rag' ? '#6ee7b7' : '#93c5fd',
                        secondaryColor: '#f3f4f6',
                        tertiaryColor: '#fef3c7',
                        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
                        fontSize: '13px',
                        sequenceNumberColor: '#6b7280',
                        noteBkgColor: mode === 'agent' ? '#f5f3ff' : mode === 'rag' ? '#ecfdf5' : '#eff6ff',
                        noteTextColor: '#374151',
                        activationBkgColor: mode === 'agent' ? '#ddd6fe' : mode === 'rag' ? '#a7f3d0' : '#bfdbfe',
                    },
                    sequence: {
                        useMaxWidth: true,
                        wrap: true,
                        wrapPadding: 10,
                        actorFontSize: 12,
                        noteFontSize: 11,
                        messageFontSize: 12,
                    },
                });

                const { svg } = await mermaid.render(idRef.current, diagramText);

                if (!cancelled && containerRef.current) {
                    containerRef.current.innerHTML = svg;
                    // Make SVG responsive
                    const svgEl = containerRef.current.querySelector('svg');
                    if (svgEl) {
                        svgEl.style.maxWidth = '100%';
                        svgEl.style.height = 'auto';
                    }
                }
            } catch (err) {
                if (!cancelled) {
                    setError(err instanceof Error ? err.message : String(err));
                }
            } finally {
                if (!cancelled) setIsRendering(false);
            }
        }

        render();
        return () => { cancelled = true; };
    }, [mode, diagramText]);

    return (
        <div className="mt-3">
            {/* Header */}
            <div className="flex items-center gap-2 mb-2">
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${mode === 'agent' ? 'bg-violet-100 text-violet-800'
                        : mode === 'rag' ? 'bg-emerald-100 text-emerald-800'
                            : 'bg-blue-100 text-blue-800'
                    }`}>
                    {mode === 'agent' ? 'Agent Pipeline' : mode === 'rag' ? 'RAG Pipeline' : 'Prompt Stuffing Pipeline'}
                </span>

                {/* Live badge — confirms diagram is derived from actual constants */}
                <span className="text-[10px] px-1.5 py-0.5 bg-yellow-50 text-yellow-700 border border-yellow-200 rounded font-mono">
                    generated from PIPELINE constants
                </span>
            </div>

            {/* Constant values summary */}
            {mode === 'rag' && (
                <div className="mb-2 flex flex-wrap gap-2 text-[10px] font-mono">
                    {[
                        ['TOP_K', `${PIPELINE.TOP_K} candidates`],
                        ['SIM_THRESHOLD', `≥ ${PIPELINE.SIM_THRESHOLD}`],
                        ['EMBEDDING_MODEL', PIPELINE.EMBEDDING_MODEL],
                        ['LLM', PIPELINE.CLAUDE_MODEL],
                        ['MAX_TOKENS', `${PIPELINE.MAX_TOKENS}`],
                    ].map(([key, val]) => (
                        <span key={key} className="px-1.5 py-0.5 bg-gray-100 rounded text-gray-600">
                            <span className="text-purple-600">{key}</span> = {val}
                        </span>
                    ))}
                </div>
            )}

            {/* Diagram */}
            {isRendering && (
                <div className="flex items-center gap-2 text-xs text-gray-400 p-4">
                    <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Rendering diagram…
                </div>
            )}

            {error && (
                <details className="text-xs text-red-500 mt-1">
                    <summary>Diagram render error</summary>
                    <pre className="mt-1 text-[10px] whitespace-pre-wrap">{error}</pre>
                    <pre className="mt-1 text-[10px] bg-gray-50 p-2 whitespace-pre-wrap">{diagramText}</pre>
                </details>
            )}

            <div
                ref={containerRef}
                className={`overflow-x-auto rounded border ${mode === 'agent' ? 'border-violet-100 bg-violet-50/30'
                        : mode === 'rag' ? 'border-emerald-100 bg-emerald-50/30'
                            : 'border-blue-100 bg-blue-50/30'
                    } p-2 ${isRendering ? 'hidden' : ''}`}
            />
        </div>
    );
}
