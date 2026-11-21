"use client";

// This component is loaded with next/dynamic { ssr: false } so @feltmaps/js-sdk
// is never evaluated on the server. The top-level import is safe here.
import { Felt, type FeltController } from "@feltmaps/js-sdk";
import { useEffect, useRef, useState } from "react";

const DRAW_TOOLS = [
  { id: "pin", label: "Pin" },
  { id: "marker", label: "Marker" },
  { id: "line", label: "Line" },
  { id: "polygon", label: "Polygon" },
  { id: "text", label: "Text" },
] as const;

interface DrawnFeature {
  id: string;
  geometry: Record<string, unknown>;
  timestamp: string;
}

interface FeltEmbedProps {
  mapId: string;
  onChangeMap: () => void;
}

export default function FeltEmbed({ mapId, onChangeMap }: FeltEmbedProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const feltRef = useRef<FeltController | null>(null);
  const [features, setFeatures] = useState<DrawnFeature[]>([]);
  const [status, setStatus] = useState("Initialising map...");
  const [activeTool, setActiveTool] = useState<string | null>(null);

  const handleToolClick = (toolId: string) => {
    if (!feltRef.current) return;
    if (activeTool === toolId) {
      feltRef.current.setTool(null);
      setActiveTool(null);
    } else {
      feltRef.current.setTool(toolId as Parameters<FeltController["setTool"]>[0]);
      setActiveTool(toolId);
    }
  };

  useEffect(() => {
    if (!containerRef.current) return;

    // Cancellation flag: prevents stale async continuations when mapId changes
    // or React StrictMode mounts/unmounts/remounts in dev.
    let cancelled = false;
    let cleanup: VoidFunction | undefined;

    containerRef.current.innerHTML = "";
    feltRef.current = null;
    setFeatures([]);
    setActiveTool(null);
    setStatus("Initialising map...");

    async function initEmbed() {
      if (!containerRef.current) return;

      try {
        const felt = await Felt.embed(containerRef.current, mapId, {
          uiControls: { showLegend: true, cooperativeGestures: false },
        });
        if (cancelled) return;

        feltRef.current = felt;
        setStatus("Map ready — select a tool and draw");

        felt.onToolChange({ handler: (tool) => setActiveTool(tool) });

        cleanup = felt.onElementCreate({
          handler: async ({ element }) => {
            if (!element) return;
            const geometry = await felt.getElementGeometry(element.id);
            setFeatures((prev) => [
              {
                id: element.id,
                geometry: geometry ?? {},
                timestamp: new Date().toISOString(),
              },
              ...prev.slice(0, 9),
            ]);
          },
        });
      } catch (err) {
        if (!cancelled) setStatus(`Embed failed: ${(err as Error).message}`);
      }
    }

    void initEmbed();

    return () => {
      cancelled = true;
      cleanup?.();
    };
  }, [mapId]);

  return (
    <div className="flex h-screen">
      {/* Map panel */}
      <div className="flex-1 relative">
        <div ref={containerRef} className="w-full h-full" />

        {/* Drawing toolbar — uiControls has no toolbar option in this SDK version */}
        <div className="absolute top-3 left-1/2 -translate-x-1/2 flex gap-1 bg-white/90 backdrop-blur-sm border border-gray-200 rounded-lg px-2 py-1.5 shadow-sm z-10">
          {DRAW_TOOLS.map((tool) => (
            <button
              key={tool.id}
              onClick={() => handleToolClick(tool.id)}
              className={`px-3 py-1 text-xs rounded-md transition-colors ${
                activeTool === tool.id
                  ? "bg-blue-600 text-white"
                  : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              {tool.label}
            </button>
          ))}
        </div>

        <div className="absolute bottom-2 left-2 flex items-center gap-2 z-10">
          <p className="text-xs text-gray-400 bg-white/80 px-2 py-1 rounded">
            {status}
          </p>
          <button
            onClick={onChangeMap}
            className="text-xs text-blue-500 bg-white/80 hover:bg-white px-2 py-1 rounded transition-colors"
          >
            Change map
          </button>
        </div>
      </div>

      {/* Geometry sidebar */}
      <aside className="w-96 border-l border-gray-200 bg-white flex flex-col">
        <header className="px-5 py-4 border-b border-gray-100">
          <h2 className="font-bold text-gray-900">Drawn Annotations</h2>
          <p className="text-xs text-gray-400 mt-1">
            Draw on the map — geometry is captured here via the JS SDK event system.
          </p>
          <p className="text-xs text-amber-500 mt-1">
            Session-only: SDK annotations are not saved back to the Felt map.
          </p>
          <p className="text-xs text-gray-300 mt-1 font-mono truncate">{mapId}</p>
        </header>
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {features.length === 0 && (
            <p className="text-sm text-gray-400 text-center mt-8">
              No annotations yet
            </p>
          )}
          {features.map((f) => (
            <div
              key={f.id}
              className="rounded-xl border border-gray-100 p-3 bg-gray-50 text-xs font-mono"
            >
              <p className="text-[10px] text-gray-400 mb-1">{f.timestamp}</p>
              <pre className="whitespace-pre-wrap break-all text-gray-700">
                {JSON.stringify(f.geometry, null, 2)}
              </pre>
            </div>
          ))}
        </div>
      </aside>
    </div>
  );
}
