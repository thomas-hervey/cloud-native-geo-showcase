/**
 * Scout Dataset Registry
 * ======================
 * Single source of truth for all datasets available in the Scout app.
 *
 * Server-side: call getAvailableDatasets() to get only datasets whose
 * parquet file actually exists in public/data/. The agent system prompt
 * and all API routes use this to avoid advertising data that isn't there.
 *
 * Client-side: use getParquetUrl() to resolve the HTTP URL for DuckDB-Wasm.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ScoutDataset {
  /** Stable identifier, matches retrieval_index.json dataset_id */
  id: string;
  /** Table alias used in SQL FROM clauses, e.g. "places" */
  tableAlias: string;
  /** Filename inside public/data/, e.g. "sf_places.parquet" */
  parquetFile: string;
  /** Human-readable label for error messages and UI */
  label: string;
  /** SELECT column allowlist — prevents geometry blob leaks */
  columns: string[];
  /** Schema description for LLM system prompt */
  schema: Record<string, string>;
  /** DuckDB-specific usage notes for LLM */
  duckdbNotes: string;
}

// ---------------------------------------------------------------------------
// Registry — add new datasets here
// ---------------------------------------------------------------------------

export const SCOUT_DATASETS: ScoutDataset[] = [
  {
    id: 'sf-places-2026',
    tableAlias: 'places',
    parquetFile: 'sf_places.parquet',
    label: 'SF Places 2026',
    columns: ['id', 'name', 'category', 'lat', 'lon'],
    schema: {
      id:       'Unique Overture Maps feature identifier (string)',
      name:     "Display name of the place, e.g. 'Blue Bottle Coffee' (string)",
      category: 'Primary place category (string)',
      lat:      'Latitude of place centroid, WGS84 decimal degrees (double)',
      lon:      'Longitude of place centroid, WGS84 decimal degrees (double)',
    },
    duckdbNotes:
      'Always write FROM places. Use ABS(lat - y) < 0.005 for proximity (~500m). ' +
      'LIMIT 200 by default. Never SELECT geometry. ' +
      'Category values are Overture snake_case strings — use ILIKE \'%keyword%\' when unsure. ' +
      'Key categories: coffee_shop, restaurant, bar, hotel, park, hospital, pharmacy, museum, gym. ' +
      'Tech: software_development, corporate_or_business_office, b2b_service. ' +
      'Retail: clothing_store, grocery_or_supermarket, specialty_store. ' +
      'Never invent category names — use ILIKE for fuzzy matching.',
  },
  {
    id: 'sf-buildings-2026',
    tableAlias: 'buildings',
    parquetFile: 'sf_buildings.parquet',
    label: 'SF Buildings 2026',
    columns: ['id', 'height', 'floors', 'use_class', 'lat', 'lon'],
    schema: {
      id:        'Unique Overture Maps building identifier (string)',
      height:    'Building height in meters (double, nullable)',
      floors:    'Number of floors above ground (integer, nullable)',
      use_class: 'Primary use: residential, commercial, industrial, civic (string, nullable)',
      lat:       'Centroid latitude, WGS84 (double)',
      lon:       'Centroid longitude, WGS84 (double)',
    },
    duckdbNotes:
      'Always write FROM buildings. Filter tall buildings: WHERE height > 30. ' +
      'Use ABS(lat - y) < 0.005 for proximity (~500m). Never SELECT geometry.',
  },
];

// ---------------------------------------------------------------------------
// Shared helpers (server + client)
// ---------------------------------------------------------------------------

/**
 * Returns the HTTP URL for a dataset's parquet file given the browser origin.
 */
export function getParquetUrl(dataset: ScoutDataset, origin: string): string {
  return `${origin}/data/${dataset.parquetFile}`;
}

/**
 * Finds the ScoutDataset for a given table alias, or undefined if not registered.
 */
export function findDatasetByAlias(tableAlias: string): ScoutDataset | undefined {
  return SCOUT_DATASETS.find((ds) => ds.tableAlias === tableAlias);
}
