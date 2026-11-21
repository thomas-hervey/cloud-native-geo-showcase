/**
 * Scout Example Queries — Shared Constants
 * =========================================
 * Shared by ChatBar (Scout page) and LabPromptBar (Lab page).
 */

/** Queries that work in all Scout modes */
export const BASE_QUERIES = [
  'Show me coffee shops near Dolores Park',
  'Find all parks in the Marina district',
  'Where are the breweries in SF?',
  'Restaurants within 500m of Union Square',
  'Show me all hospitals',
] as const;

/** RAG-mode extras (synonym routing demos) */
export const RAG_EXTRA_QUERIES = [
  'Find drugstores',
  'Show me places to eat',
] as const;

/** Agent-mode extras (multi-step demos) */
export const AGENT_EXTRA_QUERIES = [
  'Find areas with high coffee shop density but no parks nearby',
  'What neighborhood has the most restaurants?',
  'Show me tall buildings near tech companies in SoMa',
] as const;
