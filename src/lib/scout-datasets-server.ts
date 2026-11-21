/**
 * Scout Dataset Registry — Server-only helpers
 * =============================================
 * This file uses Node.js `fs` and must NEVER be imported by client components.
 * Import it only from API routes and other server-side code.
 *
 * Client-safe helpers live in scout-datasets.ts.
 */

import fs from 'fs';
import path from 'path';
import { SCOUT_DATASETS } from './scout-datasets';
import type { ScoutDataset } from './scout-datasets';

export type { ScoutDataset };

/**
 * Returns datasets whose parquet file exists in public/data/.
 * Safe to call at request time (fast synchronous fs.existsSync).
 */
export function getAvailableDatasets(): ScoutDataset[] {
  const dataDir = path.join(process.cwd(), 'public', 'data');
  return SCOUT_DATASETS.filter((ds) =>
    fs.existsSync(path.join(dataDir, ds.parquetFile))
  );
}

/**
 * Builds the ## Available datasets section of the agent system prompt.
 * Only includes datasets that exist on disk. Warns the LLM about unavailable
 * ones so it can respond gracefully instead of hallucinating table names.
 */
export function buildDatasetSystemPromptSection(): string {
  const available = getAvailableDatasets();
  if (available.length === 0) {
    return '## Available datasets\nNo datasets are currently loaded. Explain this to the user.';
  }

  const lines: string[] = ['## Available datasets'];
  lines.push(
    'CRITICAL: Use ONLY the table aliases below. NEVER use read_parquet() or any URL.'
  );
  lines.push('');

  for (const ds of available) {
    lines.push(`### \`${ds.tableAlias}\` — ${ds.label}`);
    lines.push('Columns:');
    for (const [col, desc] of Object.entries(ds.schema)) {
      lines.push(`  - \`${col}\`: ${desc}`);
    }
    lines.push(`Notes: ${ds.duckdbNotes}`);
    lines.push('');
  }

  const unavailable = SCOUT_DATASETS.filter(
    (ds) => !available.find((a) => a.id === ds.id)
  );
  if (unavailable.length > 0) {
    lines.push(
      `Datasets NOT currently loaded: ${unavailable.map((d) => d.label).join(', ')}. ` +
      'If asked about these, explain they are not currently available.'
    );
  }

  return lines.join('\n');
}
