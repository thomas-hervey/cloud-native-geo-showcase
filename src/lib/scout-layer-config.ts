/**
 * Scout Layer Config Converters
 * ==============================
 * Pure functions — no React, no side effects.
 * Convert LayerConfig to MapLibre paint property objects.
 *
 * Used by:
 *   - src/app/scout/lab/components/LabMap.tsx
 */

import type { LayerConfig } from './scout-types';

/**
 * Convert LayerConfig to MapLibre circle paint properties.
 * Returns a plain object keyed by MapLibre paint property names.
 */
export function toCirclePaint(cfg: LayerConfig): Record<string, unknown> {
  return {
    'circle-color': `rgb(${cfg.color[0]}, ${cfg.color[1]}, ${cfg.color[2]})`,
    'circle-radius': cfg.radius,
    'circle-opacity': cfg.opacity,
    'circle-stroke-width': 1.5,
    'circle-stroke-color': '#ffffff',
  };
}

/**
 * Convert LayerConfig to MapLibre heatmap paint properties.
 * The color and radius are derived from the LayerConfig to maintain
 * consistent visual identity with the circle variant.
 */
export function toHeatmapPaint(cfg: LayerConfig): Record<string, unknown> {
  return {
    'heatmap-weight': 1,
    'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 0, 1, 15, 3],
    'heatmap-color': [
      'interpolate',
      ['linear'],
      ['heatmap-density'],
      0, 'rgba(0, 0, 255, 0)',
      0.2, `rgba(${cfg.color[0]}, ${cfg.color[1]}, ${cfg.color[2]}, 0.3)`,
      0.4, `rgba(${cfg.color[0]}, ${cfg.color[1]}, ${cfg.color[2]}, 0.5)`,
      0.6, `rgba(${cfg.color[0]}, ${cfg.color[1]}, ${cfg.color[2]}, 0.7)`,
      1, `rgba(${cfg.color[0]}, ${cfg.color[1]}, ${cfg.color[2]}, ${cfg.opacity})`,
    ],
    'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 0, 2, 15, cfg.radius * 2],
    'heatmap-opacity': cfg.opacity,
  };
}

/** Default config when LLM returns nothing or returns an invalid config */
export const DEFAULT_LAYER_CONFIG: LayerConfig = {
  type: 'circle',
  color: [99, 102, 241],   // indigo — neutral, works for any data
  radius: 7,
  opacity: 0.85,
};
