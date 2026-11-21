'use client';

import replayIndexJson from '@/content/scout-replays/index.json';
import { ReplayIndexSchema, type ReplayIndexEntry } from '@/lib/scout-replay';

const EXAMPLES: ReplayIndexEntry[] = ReplayIndexSchema.parse(replayIndexJson);

interface RecordedRunExamplesProps {
  onSelect: (id: string) => void;
  disabled?: boolean;
}

/** Example chips that replay a recorded Scout run. Shown when live LLM is off. */
export default function RecordedRunExamples({ onSelect, disabled = false }: RecordedRunExamplesProps) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {EXAMPLES.map((example) => (
        <button
          key={example.id}
          type="button"
          onClick={() => onSelect(example.id)}
          disabled={disabled}
          title={example.query}
          className="text-[11px] px-2 py-0.5 rounded-full bg-slate-50 text-slate-600 hover:bg-slate-100 border border-slate-200 transition-colors disabled:opacity-50"
        >
          {example.title}
        </button>
      ))}
    </div>
  );
}
