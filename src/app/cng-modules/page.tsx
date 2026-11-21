import React from 'react';
import Link from 'next/link';
import { getCurriculum } from '@/lib/curriculum';
import {
  BookOpen,
  CheckCircle,
  Circle,
  PlayCircle,
  Layers,
  ArrowRight,
  Sparkles,
  Zap,
  Globe,
  Database,
  Cpu
} from 'lucide-react';

export default function CurriculumIndex() {
  const curriculum = getCurriculum();

  const getStatusIcon = (status: string) => {
    const tooltipText = {
      'complete': 'All exercises and content finished.',
      'in_progress': 'Currently being updated with new content.',
      'planned': 'Coming soon to the curriculum.'
    }[status] || '';

    const icon = {
      'complete': <CheckCircle className="w-5 h-5 text-emerald-500" />,
      'in_progress': <PlayCircle className="w-5 h-5 text-amber-500 animate-pulse" />,
      'planned': <Circle className="w-5 h-5 text-gray-300" />
    }[status] || null;

    if (!icon) return null;

    return (
      <div className="relative group/status">
        {icon}
        <div className="absolute bottom-full right-0 mb-2 hidden group-hover/status:block w-48 p-2 bg-gray-900 text-white text-[10px] font-bold rounded-lg shadow-xl z-50 text-center leading-tight">
          {tooltipText}
          <div className="absolute top-full right-2 border-8 border-transparent border-t-gray-900" />
        </div>
      </div>
    );
  };

  const getTrackIcon = (trackId: string) => {
    switch (trackId) {
      case 'fundamentals': return <Database className="w-6 h-6 text-blue-500" />;
      case 'product-patterns': return <Zap className="w-6 h-6 text-amber-500" />;
      case 'analysis-viz': return <Sparkles className="w-6 h-6 text-purple-500" />;
      case 'scout-project': return <Globe className="w-6 h-6 text-emerald-500" />;
      case 'geo-ai': return <Cpu className="w-6 h-6 text-rose-500" />;
      default: return <BookOpen className="w-6 h-6 text-blue-500" />;
    }
  };

  return (
    <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-12 py-16">
      {/* Hero Section */}
      <header className="mb-20 text-center">
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-blue-50 text-blue-700 rounded-full text-sm font-black uppercase tracking-widest border border-blue-100 mb-6 shadow-sm">
          <BookOpen className="w-4 h-4" />
          Interactive Curriculum
        </div>
        <h1 className="text-5xl md:text-7xl font-black text-gray-900 mb-6 tracking-tight leading-none bg-clip-text text-transparent bg-gradient-to-br from-gray-900 to-gray-500">
          Cloud-Native Geospatial
        </h1>
        <p className="text-xl md:text-2xl text-gray-500 max-w-3xl mx-auto leading-relaxed">
          The comprehensive self-learning platform for modern spatial data engineering, AI, and visualization.
        </p>
      </header>

      {/* Track Listing */}
      <div className="space-y-24">
        {curriculum.tracks.map((track, trackIdx) => (
          <section key={track.id} className="relative">
            <div className="flex flex-col lg:flex-row gap-12 items-start">
              {/* Track Sidebar */}
              <div className="lg:w-1/3 lg:sticky lg:top-24">
                <div className="p-1 rounded-3xl bg-gradient-to-br from-gray-100 to-white shadow-sm border border-gray-100">
                  <div className="bg-white rounded-[1.4rem] p-8 shadow-inner">
                    <div className="w-12 h-12 rounded-2xl bg-gray-50 border border-gray-100 flex items-center justify-center mb-6 shadow-sm">
                      {getTrackIcon(track.id)}
                    </div>
                    <h2 className="text-3xl font-black text-gray-900 mb-4 tracking-tight leading-tight">
                      {track.title}
                    </h2>
                    <p className="text-gray-500 font-medium leading-relaxed mb-6">
                      {track.description}
                    </p>
                    <div className="flex items-center gap-3 text-xs font-black text-gray-400 uppercase tracking-widest">
                      <Layers className="w-4 h-4" />
                      {track.modules.length} Modules in this path
                    </div>
                  </div>
                </div>
              </div>

              {/* Module Grid */}
              <div className="lg:w-2/3 grid grid-cols-1 md:grid-cols-2 gap-6">
                {track.modules.map((slug, moduleIdx) => {
                  const mod = curriculum.modules[slug];
                  if (!mod) return null;

                  return (
                    <Link
                      key={slug}
                      href={`/cng-modules/${slug}`}
                      className="group relative bg-white rounded-3xl border border-gray-100 p-6 shadow-sm hover:shadow-2xl hover:border-blue-200 transition-all duration-300"
                    >
                      {/* Metadata Tooltip (Appears above card) */}
                      <div className="absolute inset-x-4 bottom-full mb-4 z-50 opacity-0 group-hover:opacity-100 transition-all duration-300 pointer-events-none translate-y-2 group-hover:translate-y-0">
                        <div className="bg-gray-900/95 backdrop-blur-sm text-white p-4 rounded-2xl shadow-2xl border border-white/10 ring-1 ring-black/5">
                          <div className="space-y-3">
                            <div>
                              <p className="text-[10px] font-black uppercase tracking-widest text-blue-400 mb-1.5 flex items-center gap-1.5">
                                <Sparkles className="w-3 h-3" />
                                Techniques Learned
                              </p>
                              <div className="flex flex-wrap gap-1.5">
                                {mod.techniques?.map((t, i) => (
                                  <span key={i} className="text-[9px] bg-white/10 px-2 py-0.5 rounded-full border border-white/5 font-bold">{t}</span>
                                ))}
                              </div>
                            </div>
                            <div>
                              <p className="text-[10px] font-black uppercase tracking-widest text-emerald-400 mb-1.5 flex items-center gap-1.5">
                                <Zap className="w-3 h-3" />
                                Tools Introduced
                              </p>
                              <div className="flex flex-wrap gap-1.5">
                                {mod.tools?.map((t, i) => (
                                  <span key={i} className="text-[9px] bg-white/10 px-2 py-0.5 rounded-full border border-white/5 font-bold">{t}</span>
                                ))}
                              </div>
                            </div>
                          </div>
                        </div>
                        {/* Tooltip Arrow */}
                        <div className="absolute top-full left-1/2 -translate-x-1/2 border-8 border-transparent border-t-gray-900/95" />
                      </div>

                      {/* Decorative Background */}
                      <div className="absolute top-0 right-0 w-32 h-32 bg-blue-50/20 rounded-full blur-3xl -mr-16 -mt-16 group-hover:bg-blue-100/40 transition-colors" />

                      <div className="relative flex flex-col h-full">
                        <div className="flex items-center justify-between mb-4">
                          <span className="text-[10px] font-black font-mono text-gray-300 group-hover:text-blue-200 transition-colors">
                            {String(trackIdx + 1).padStart(2, '0')}.{String(moduleIdx + 1).padStart(2, '0')}
                          </span>
                          {getStatusIcon(mod.status)}
                        </div>

                        <h3 className="text-xl font-black text-gray-900 mb-2 group-hover:text-blue-700 transition-colors leading-tight">
                          {mod.title}
                        </h3>

                        <div className="flex flex-col gap-2">
                          <p className="text-sm text-gray-500 font-medium leading-relaxed italic">
                            {mod.description}
                            <span className="inline-flex items-center gap-1 ml-2 text-blue-600 font-black text-[10px] group-hover:text-blue-800 transition-all uppercase tracking-widest leading-none">
                              Go
                              <ArrowRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
                            </span>
                          </p>
                        </div>
                      </div>
                    </Link>
                  );
                })}
              </div>
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
