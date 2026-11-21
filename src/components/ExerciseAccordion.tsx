'use client';

import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import ModuleContent from '@/components/ModuleContent';

interface ExerciseFile {
  filename: string;
  content: string;
  language: string;
}

interface ExerciseAccordionProps {
  files: ExerciseFile[];
}

function ExerciseItem({ file }: { file: ExerciseFile }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="group bg-white rounded-3xl border border-gray-100 overflow-hidden shadow-sm hover:shadow-xl transition-all duration-300">
      {/* Clickable header */}
      <button
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        className="w-full text-left bg-gray-50 px-6 py-4 border-b border-gray-100 flex justify-between items-center group-hover:bg-indigo-50 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 focus-visible:ring-inset"
      >
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-indigo-400 shrink-0" />
          <span className="font-mono text-sm text-gray-700 font-bold">{file.filename}</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[10px] text-indigo-500 bg-white px-2 py-1 rounded-full border border-indigo-100 uppercase font-black tracking-widest leading-none shadow-sm">
            {file.language}
          </span>
          <ChevronDown
            className={`w-4 h-4 text-indigo-400 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
          />
        </div>
      </button>

      {/* Collapsible body */}
      {open && (
        <div className="p-0">
          <ModuleContent content={`\`\`\`${file.language}\n${file.content}\n\`\`\``} />
        </div>
      )}
    </div>
  );
}

export default function ExerciseAccordion({ files }: ExerciseAccordionProps) {
  return (
    <div className="space-y-4">
      {files.map((file) => (
        <ExerciseItem key={file.filename} file={file} />
      ))}
    </div>
  );
}
