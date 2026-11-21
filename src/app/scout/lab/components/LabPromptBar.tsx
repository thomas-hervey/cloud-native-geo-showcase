/**
 * LabPromptBar — Shared Prompt Bar for Scout Lab
 * ===========================================================
 * Used in "unified" mode: a single query fires both the left (Scout agent)
 * and right (Generative UI) maps simultaneously.
 *
 * Neutral gray/slate color scheme — not tied to any specific Scout mode.
 */

'use client';

import { useState, useRef } from 'react';
import { BASE_QUERIES } from '@/lib/scout-queries';

interface LabPromptBarProps {
  onQuery: (text: string) => void;
  isLoading?: boolean;
}

export default function LabPromptBar({ onQuery, isLoading = false }: LabPromptBarProps) {
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed || isLoading) return;
    onQuery(trimmed);
  };

  return (
    <div>
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Query both maps..."
          disabled={isLoading}
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed text-sm"
        />
        <button
          type="submit"
          disabled={isLoading || !query.trim()}
          className="px-5 py-2 text-white rounded-lg transition-colors text-sm font-medium whitespace-nowrap bg-slate-600 hover:bg-slate-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          {isLoading ? (
            <span className="flex items-center gap-2">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Scouting...
            </span>
          ) : (
            'Scout both'
          )}
        </button>
      </form>

      {/* Example query chips — same BASE_QUERIES used in ChatBar */}
      <div className="mt-2 flex flex-wrap gap-1.5">
        {BASE_QUERIES.map((example) => (
          <button
            key={example}
            onClick={() => { setQuery(example); inputRef.current?.focus(); }}
            disabled={isLoading}
            className="text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-600 hover:bg-slate-100 hover:text-slate-700 transition-colors disabled:opacity-50"
          >
            {example}
          </button>
        ))}
      </div>
    </div>
  );
}
