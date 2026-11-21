/**
 * PipelineModal — full-screen modal wrapper for the Scout pipeline diagram.
 *
 * Replaces the <details> accordion in page.tsx so the diagram gets room
 * to breathe and the map isn't pushed off screen.
 *
 * Usage:
 *   <PipelineModal mode={mode} />
 *
 * Renders a small "How this works" trigger button.
 * Clicking it opens a backdrop modal with a scrollable diagram inside.
 * ESC key or clicking the backdrop closes it.
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import dynamic from 'next/dynamic';
import type { Mode } from '@/lib/scout-types';

const PipelineDiagram = dynamic(
    () => import('./PipelineDiagram'),
    { ssr: false, loading: () => <div className="text-xs text-gray-400 p-6 text-center animate-pulse">Loading diagram…</div> }
);

interface PipelineModalProps {
    mode: Mode;
}

const MODAL_TITLE: Record<Mode, string> = {
    stuffing: 'Prompt Stuffing Pipeline',
    rag: 'RAG Pipeline',
    agent: 'Agent Pipeline',
};

const TRIGGER_COLOR: Record<Mode, string> = {
    stuffing: 'text-blue-600 hover:text-blue-800',
    rag: 'text-emerald-700 hover:text-emerald-900',
    agent: 'text-violet-700 hover:text-violet-900',
};

const HEADER_COLOR: Record<Mode, string> = {
    stuffing: 'bg-blue-50 border-blue-200 text-blue-900',
    rag: 'bg-emerald-50 border-emerald-200 text-emerald-900',
    agent: 'bg-violet-50 border-violet-200 text-violet-900',
};

export default function PipelineModal({ mode }: PipelineModalProps) {
    const [open, setOpen] = useState(false);

    const close = useCallback(() => setOpen(false), []);

    // ESC to close
    useEffect(() => {
        if (!open) return;
        const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') close(); };
        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, [open, close]);

    // Prevent body scroll when open
    useEffect(() => {
        document.body.style.overflow = open ? 'hidden' : '';
        return () => { document.body.style.overflow = ''; };
    }, [open]);

    return (
        <>
            {/* Trigger */}
            <button
                onClick={() => setOpen(true)}
                className={`text-xs font-medium flex items-center gap-1 ${TRIGGER_COLOR[mode]}`}
            >
                <span>⚙</span>
                How this works — {MODAL_TITLE[mode].split(' — ')[0]}
            </button>

            {/* Modal */}
            {open && (
                <div
                    className="fixed inset-0 z-50 flex items-start justify-center pt-10 px-4 pb-10"
                    style={{ background: 'rgba(0,0,0,0.55)' }}
                    onClick={(e) => { if (e.target === e.currentTarget) close(); }}
                >
                    <div
                        className="relative bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[85vh] flex flex-col"
                        onClick={(e) => e.stopPropagation()}
                    >
                        {/* Header */}
                        <div className={`flex items-center justify-between px-5 py-3 rounded-t-2xl border-b ${HEADER_COLOR[mode]}`}>
                            <div>
                                <h2 className="font-semibold text-sm">{MODAL_TITLE[mode]}</h2>
                                <p className="text-xs opacity-70 mt-0.5">
                                    Sequence diagram generated live from <code className="font-mono">PIPELINE</code> constants
                                </p>
                            </div>
                            <button
                                onClick={close}
                                className="text-gray-400 hover:text-gray-700 text-xl leading-none px-2"
                                aria-label="Close"
                            >
                                ✕
                            </button>
                        </div>

                        {/* Scrollable body */}
                        <div className="overflow-y-auto overflow-x-auto flex-1 p-5">
                            <PipelineDiagram mode={mode} />
                        </div>

                        {/* Footer */}
                        <div className="px-5 py-2 border-t border-gray-100 rounded-b-2xl flex justify-end">
                            <button
                                onClick={close}
                                className="text-xs text-gray-500 hover:text-gray-700 px-3 py-1 rounded hover:bg-gray-100"
                            >
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
