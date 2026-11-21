import React from 'react';
import { ModuleMetadata, type CNGModuleMetadata } from '@/lib/curriculum';
import { Tag, Cpu, Bookmark, CheckCircle, Clock } from 'lucide-react';

interface ModuleHeaderProps {
  metadata: ModuleMetadata;
}

export default function ModuleHeader({ metadata }: ModuleHeaderProps) {
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'complete':
        return (
          <span className="inline-flex items-center gap-1.5 bg-emerald-50 text-emerald-700 px-3 py-1 rounded-full text-xs font-bold border border-emerald-100 shadow-sm">
            <CheckCircle className="w-3.5 h-3.5" />
            Complete
          </span>
        );
      case 'in_progress':
        return (
          <span className="inline-flex items-center gap-1.5 bg-amber-50 text-amber-700 px-3 py-1 rounded-full text-xs font-bold border border-amber-100 shadow-sm animate-pulse">
            <Clock className="w-3.5 h-3.5" />
            In Progress
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 bg-gray-50 text-gray-700 px-3 py-1 rounded-full text-xs font-bold border border-gray-100">
            Planned
          </span>
        );
    }
  };

  return (
    <div className="mb-10 pb-8 border-b border-gray-100">
      <div className="flex flex-wrap items-center gap-3 mb-4">
        {getStatusBadge(metadata.status)}
        <span className="inline-flex items-center gap-1.5 bg-blue-50 text-blue-700 px-3 py-1 rounded-full text-xs font-bold border border-blue-100 shadow-sm">
          <Bookmark className="w-3.5 h-3.5" />
          {metadata.track}
        </span>
        {(metadata as CNGModuleMetadata).type && (
          <span className="inline-flex items-center gap-1.5 bg-violet-50 text-violet-700 px-3 py-1 rounded-full text-xs font-bold border border-violet-100 shadow-sm capitalize">
            {(metadata as CNGModuleMetadata).type}
          </span>
        )}
      </div>

      <h1 className="text-4xl md:text-5xl font-black text-gray-900 mb-4 tracking-tight leading-tight">
        {metadata.title}
      </h1>
      
      <p className="text-xl text-gray-500 leading-relaxed max-w-3xl mb-8">
        {metadata.description}
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 p-6 bg-gradient-to-br from-gray-50 to-white rounded-2xl border border-gray-100 shadow-inner">
        <div>
          <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3 flex items-center gap-2">
            <Tag className="w-3.5 h-3.5" />
            Techniques Learned
          </h3>
          <div className="flex flex-wrap gap-2">
            {metadata.techniques?.map((t, idx) => (
              <span key={idx} className="bg-white text-gray-700 px-2.5 py-1 rounded-md text-[11px] font-bold shadow-sm border border-gray-200">
                {t}
              </span>
            ))}
          </div>
        </div>
        <div>
          <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3 flex items-center gap-2">
            <Cpu className="w-3.5 h-3.5" />
            Tools Introduced
          </h3>
          <div className="flex flex-wrap gap-2">
            {metadata.tools?.map((t, idx) => (
              <span key={idx} className="bg-indigo-50 text-indigo-700 px-2.5 py-1 rounded-md text-[11px] font-bold border border-indigo-100">
                {t}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
