/**
 * LayerConfigInspector
 * ====================
 * Collapsible panel showing the LLM's visualization decisions:
 *   - Color swatch
 *   - Human-readable label + reasoning
 *   - Raw JSON of the layer_config
 *
 * Uses amber/yellow color scheme to distinguish it from the violet agent
 * trace and emerald RAG panels in the existing Scout page.
 */

'use client';

import type { LayerConfig } from '@/lib/scout-types';

interface LayerConfigInspectorProps {
  layerConfig: LayerConfig;
  reasoning: string;
}

export default function LayerConfigInspector({ layerConfig, reasoning }: LayerConfigInspectorProps) {
  const rgbStr = `rgb(${layerConfig.color.join(', ')})`;

  return (
    <details className="mt-2" open>
      <summary className="cursor-pointer text-xs font-medium text-amber-700 hover:text-amber-900 flex items-center gap-2">
        <span
          className="w-3 h-3 rounded-full inline-block flex-shrink-0 border border-amber-300"
          style={{ backgroundColor: rgbStr }}
        />
        <span>Generative style</span>
        <span className="font-mono font-normal text-amber-600 ml-1">
          {layerConfig.type} · r={layerConfig.radius} · α={layerConfig.opacity}
        </span>
      </summary>

      <div className="mt-1 rounded border border-amber-200 bg-amber-50 p-2 space-y-2 text-xs">
        {/* Color swatch + label */}
        <div className="flex items-center gap-2">
          <div
            className="w-6 h-6 rounded flex-shrink-0 border border-amber-300 shadow-sm"
            style={{ backgroundColor: rgbStr }}
            title={`rgb(${layerConfig.color.join(', ')})`}
          />
          <div>
            {layerConfig.label && (
              <p className="font-medium text-amber-900">{layerConfig.label}</p>
            )}
            <p className="text-amber-700 font-mono">rgb({layerConfig.color.join(', ')})</p>
          </div>
        </div>

        {/* LLM reasoning */}
        {reasoning && (
          <div>
            <p className="text-[10px] text-amber-500 uppercase tracking-wide font-medium mb-0.5">
              Reasoning
            </p>
            <p className="text-amber-800 leading-relaxed">{reasoning}</p>
          </div>
        )}

        {/* Raw JSON */}
        <details>
          <summary className="cursor-pointer text-amber-500 hover:text-amber-700 text-[10px]">
            Raw layer_config JSON
          </summary>
          <pre className="mt-1 text-[10px] font-mono text-amber-800 bg-white/60 p-1.5 rounded overflow-x-auto whitespace-pre-wrap">
            {JSON.stringify(layerConfig, null, 2)}
          </pre>
        </details>
      </div>
    </details>
  );
}
