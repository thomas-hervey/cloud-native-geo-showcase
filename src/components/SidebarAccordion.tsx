'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { ChevronDown, ChevronRight, BookOpen, Layers, CheckCircle, Circle, PlayCircle } from 'lucide-react';
import { Curriculum, type CNGModuleMetadata } from '@/lib/curriculum';

interface SidebarAccordionProps {
  curriculum: Curriculum;
  currentSlug: string;
  headings?: { text: string; anchor: string }[];
}

export default function SidebarAccordion({ curriculum, currentSlug, headings }: SidebarAccordionProps) {
  // Find which track the current module belongs to and open it by default
  const [openTracks, setOpenTracks] = useState<Record<string, boolean>>(() => {
    const initial: Record<string, boolean> = {};
    curriculum.tracks.forEach(track => {
      if (track.modules.includes(currentSlug)) {
        initial[track.id] = true;
      }
    });
    return initial;
  });

  const toggleTrack = (trackId: string) => {
    setOpenTracks(prev => ({
      ...prev,
      [trackId]: !prev[trackId]
    }));
  };

  const getStatusIcon = (status: string) => {
    const tooltipText = {
      'complete': "Thomas has finished learning and building this module.",
      'in_progress': "Thomas is actively working through this module.",
      'planned': "Planned for a future learning session."
    }[status] || '';

    const icon = {
      'complete': <CheckCircle className="w-3.5 h-3.5 text-green-500" />,
      'in_progress': <PlayCircle className="w-3.5 h-3.5 text-blue-500 animate-pulse" />,
      'planned': <Circle className="w-3.5 h-3.5 text-gray-300" />
    }[status] || null;

    if (!icon) return null;

    return (
      <div className="relative group/status">
        {icon}
        <div className="absolute bottom-full right-0 mb-2 hidden group-hover/status:block w-32 p-2 bg-gray-900 text-white text-[9px] font-bold rounded-lg shadow-xl z-50 text-center leading-tight">
          {tooltipText}
          <div className="absolute top-full right-1.5 border-4 border-transparent border-t-gray-900" />
        </div>
      </div>
    );
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-xl overflow-hidden sticky top-8">
      <div className="bg-gradient-to-r from-blue-700 to-indigo-800 p-5">
        <h2 className="text-lg font-bold text-white flex items-center gap-2">
          <BookOpen className="w-5 h-5" />
          Curriculum
        </h2>
      </div>

      <div className="p-2 max-h-[75vh] overflow-y-auto custom-scrollbar">
        {curriculum.tracks.map((track) => {
          const isOpen = openTracks[track.id];
          const isActiveTrack = track.modules.includes(currentSlug);

          return (
            <div key={track.id} className="mb-2">
              <button
                onClick={() => toggleTrack(track.id)}
                className={`w-full flex items-center justify-between p-3 rounded-lg text-left transition-all duration-200 ${
                  isActiveTrack
                    ? 'bg-blue-50 text-blue-900 border border-blue-100 shadow-sm'
                    : 'hover:bg-gray-50 text-gray-700'
                }`}
              >
                <div className="flex items-center gap-2">
                  {isOpen ? <ChevronDown className="w-4 h-4 text-blue-500" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
                  <span className="text-sm font-bold tracking-tight">
                    {track.title.split(': ')[1] || track.title}
                  </span>
                </div>
                <span className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded font-mono">
                  {track.modules.length}
                </span>
              </button>

              {isOpen && (
                <div className="mt-1 ml-4 space-y-1 border-l-2 border-blue-50 pl-2 py-1 animate-in fade-in slide-in-from-top-2 duration-300">
                  {track.modules.map((slug) => {
                    const moduleData = curriculum.modules[slug];
                    const isActive = slug === currentSlug;
                    if (!moduleData) return null;

                    return (
                      <React.Fragment key={slug}>
                        <Link
                          href={`/cng-modules/${slug}`}
                          className={`group flex items-center justify-between p-2 rounded-md text-xs transition-all relative ${
                            isActive
                              ? 'bg-blue-600 text-white font-semibold shadow-md translate-x-1'
                              : 'text-gray-600 hover:bg-white hover:shadow-sm hover:translate-x-1'
                          }`}
                        >
                          {/* Tooltip for Sidebar (Appears above/side) */}
                          <div className="absolute bottom-full left-0 mb-2 z-50 opacity-0 group-hover:opacity-100 transition-all duration-300 pointer-events-none translate-y-2 group-hover:translate-y-0 w-48">
                            <div className="bg-gray-900/95 backdrop-blur-sm text-white p-3 rounded-xl shadow-2xl border border-white/10 ring-1 ring-black/5">
                              <div className="space-y-2">
                                <div>
                                  <p className="text-[8px] font-black uppercase tracking-widest text-blue-400 mb-1 leading-none">Techniques</p>
                                  <div className="flex flex-wrap gap-1 mt-1">
                                    {(moduleData as CNGModuleMetadata).techniques?.slice(0, 3).map((t, i) => (
                                      <span key={i} className="text-[7px] bg-white/10 px-1.5 py-0.5 rounded-full border border-white/5 font-bold leading-none">{t}</span>
                                    ))}
                                  </div>
                                </div>
                                <div>
                                  <p className="text-[8px] font-black uppercase tracking-widest text-emerald-400 mb-1 leading-none">Tools</p>
                                  <div className="flex flex-wrap gap-1 mt-1">
                                    {(moduleData as CNGModuleMetadata).tools?.slice(0, 3).map((t, i) => (
                                      <span key={i} className="text-[7px] bg-white/10 px-1.5 py-0.5 rounded-full border border-white/5 font-bold leading-none">{t}</span>
                                    ))}
                                  </div>
                                </div>
                                {(moduleData as CNGModuleMetadata).type && (
                                  <div>
                                    <p className="text-[8px] font-black uppercase tracking-widest text-violet-400 mb-1 leading-none">Type</p>
                                    <span className="text-[7px] bg-white/10 px-1.5 py-0.5 rounded-full border border-white/5 font-bold leading-none capitalize">
                                      {(moduleData as CNGModuleMetadata).type}
                                    </span>
                                  </div>
                                )}
                              </div>
                            </div>
                            {/* Arrow pointing down to the link */}
                            <div className="absolute top-full left-4 border-4 border-transparent border-t-gray-900/95" />
                          </div>

                          <div className="flex items-center gap-2 overflow-hidden">
                            <span className="truncate">{moduleData.title}</span>
                          </div>
                          <div className="flex-shrink-0">
                            {isActive ? <Layers className="w-3.5 h-3.5 text-blue-200" /> : getStatusIcon(moduleData.status)}
                          </div>
                        </Link>

                        {isActive && headings && headings.length > 0 && (
                          <div className="ml-3 mt-0.5 mb-1 border-l-2 border-blue-200 pl-2 space-y-0.5">
                            {headings.map(h => (
                              <a
                                key={h.anchor}
                                href={`#${h.anchor}`}
                                className="block text-[10px] text-gray-500 hover:text-blue-700 py-0.5 truncate leading-tight transition-colors"
                              >
                                {h.text}
                              </a>
                            ))}
                          </div>
                        )}
                      </React.Fragment>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
