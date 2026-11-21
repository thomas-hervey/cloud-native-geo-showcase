/**
 * Scout SQL Guards & DuckDB-Wasm Utilities
 * ==========================================
 * Used by:
 *   - Server: all three /api/scout/* routes (validateSql, enforceLimitClause)
 *   - Client: ScoutMap.tsx (rewriteSqlForWasm, checkParquetReachable)
 *
 * Key guarantees:
 *   1. No DDL/DML reaches DuckDB-Wasm (validateSql)
 *   2. Results are always bounded (enforceLimitClause)
 *   3. Table aliases are always resolved to local parquet URLs (rewriteSqlForWasm)
 *   4. Missing data files surface a user-friendly error (checkParquetReachable)
 */

import { SCOUT_DATASETS } from './scout-datasets';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ValidationResult {
  valid: boolean;
  reason?: string;
}

export class DataUnavailableError extends Error {
  constructor(
    message: string,
    public readonly datasetLabel: string,
    public readonly parquetUrl: string,
  ) {
    super(message);
    this.name = 'DataUnavailableError';
  }
}

// ---------------------------------------------------------------------------
// SQL validation (server-side)
// ---------------------------------------------------------------------------

/** Patterns that must never appear in LLM-generated SQL sent to DuckDB-Wasm. */
const FORBIDDEN_PATTERNS: Array<{ re: RegExp; label: string }> = [
  { re: /\bDROP\b/i,          label: 'DROP statement' },
  { re: /\bDELETE\b/i,        label: 'DELETE statement' },
  { re: /\bINSERT\b/i,        label: 'INSERT statement' },
  { re: /\bUPDATE\b/i,        label: 'UPDATE statement' },
  { re: /\bCREATE\b/i,        label: 'CREATE statement' },
  { re: /\bTRUNCATE\b/i,      label: 'TRUNCATE statement' },
  { re: /\bALTER\b/i,         label: 'ALTER statement' },
  { re: /\bGRANT\b/i,         label: 'GRANT statement' },
  { re: /\bREVOKE\b/i,        label: 'REVOKE statement' },
  { re: /\bEXEC(?:UTE)?\b/i,  label: 'EXEC/EXECUTE statement' },
  // Multiple SELECT statements via semicolon chaining
  { re: /SELECT[\s\S]+;[\s\S]*SELECT/i, label: 'multiple SELECT statements (semicolon chaining)' },
];

/**
 * Returns { valid: true } if the SQL is safe to send to DuckDB-Wasm.
 * Returns { valid: false, reason } if a forbidden pattern is found.
 */
export function validateSql(sql: string): ValidationResult {
  for (const { re, label } of FORBIDDEN_PATTERNS) {
    if (re.test(sql)) {
      return { valid: false, reason: `Forbidden SQL pattern detected: ${label}` };
    }
  }
  return { valid: true };
}

// ---------------------------------------------------------------------------
// LIMIT enforcement (server-side)
// ---------------------------------------------------------------------------

/**
 * Ensures the SQL has a LIMIT clause no larger than `max`.
 * - If no LIMIT: appends LIMIT max
 * - If LIMIT > max: clamps to max
 * - If LIMIT <= max: leaves unchanged
 */
export function enforceLimitClause(sql: string, max = 500): string {
  const limitRe = /\bLIMIT\s+(\d+)/i;
  const match = sql.match(limitRe);

  if (!match) {
    return sql.trimEnd().replace(/;?\s*$/, '') + `\nLIMIT ${max};`;
  }

  const existing = parseInt(match[1], 10);
  if (existing > max) {
    return sql.replace(limitRe, `LIMIT ${max}`);
  }

  return sql;
}

// ---------------------------------------------------------------------------
// SQL rewrite for DuckDB-Wasm (shared server + client)
// ---------------------------------------------------------------------------

/**
 * Rewrites SQL table alias references to read_parquet(url) for DuckDB-Wasm.
 *
 * Handles:
 *   1. FROM places     → FROM read_parquet('http://localhost:3000/data/sf_places.parquet')
 *   2. FROM buildings  → FROM read_parquet('http://localhost:3000/data/sf_buildings.parquet')
 *   3. JOIN places / JOIN buildings — same rewrite
 *   4. Hallucinated    → read_parquet('https://data.sfscout.org/...') → correct local URL
 *   5. Strips LOAD xyz; lines — extensions are loaded during DuckDB-Wasm init
 *
 * @param sql    The SQL string from the LLM (may contain LOAD statements)
 * @param origin Browser origin, e.g. 'http://localhost:3000'
 */
export function rewriteSqlForWasm(sql: string, origin: string): string {
  // Strip LOAD statements — extensions are loaded during DuckDB-Wasm init
  let rewritten = sql.replace(/LOAD\s+\w+;\s*/gi, '');

  // Rewrite each registered table alias → read_parquet(local url)
  for (const ds of SCOUT_DATASETS) {
    const parquetUrl = `${origin}/data/${ds.parquetFile}`;
    // Match FROM/JOIN followed by the alias as a whole word
    const aliasRe = new RegExp(`\\b(FROM|JOIN)\\s+${ds.tableAlias}\\b`, 'gi');
    rewritten = rewritten.replace(aliasRe, `$1 read_parquet('${parquetUrl}')`);
  }

  // Safety net: redirect hallucinated https:// read_parquet URLs to the
  // correct local file based on dataset name matching in the URL
  for (const ds of SCOUT_DATASETS) {
    const parquetUrl = `${origin}/data/${ds.parquetFile}`;
    const namePattern = ds.tableAlias.replace(/[-]/g, '[_-]');
    const remoteRe = new RegExp(
      `read_parquet\\('https?://[^']*${namePattern}[^']*'\\)`,
      'gi'
    );
    rewritten = rewritten.replace(remoteRe, `read_parquet('${parquetUrl}')`);
  }

  // Catch-all: replace genuinely external (https://) read_parquet URLs.
  // Uses https:// (not https?://) so local http://localhost URLs are never matched.
  if (SCOUT_DATASETS.length > 0) {
    const fallbackUrl = `${origin}/data/${SCOUT_DATASETS[0].parquetFile}`;
    rewritten = rewritten.replace(
      /read_parquet\('https:\/\/[^']+'\)/gi,
      `read_parquet('${fallbackUrl}')`
    );
  }

  return rewritten;
}

/**
 * Extracts all read_parquet() URLs from a rewritten SQL string,
 * paired with the dataset label for user-facing messages.
 */
export function extractParquetUrls(sql: string): Array<{ url: string; label: string }> {
  const results: Array<{ url: string; label: string }> = [];
  const re = /read_parquet\('([^']+)'\)/gi;
  let match: RegExpExecArray | null;
  const seen = new Set<string>();

  while ((match = re.exec(sql)) !== null) {
    const url = match[1];
    if (seen.has(url)) continue;
    seen.add(url);

    const filename = url.split('/').pop() ?? '';
    const ds = SCOUT_DATASETS.find((d) => d.parquetFile === filename);
    results.push({ url, label: ds?.label ?? filename });
  }

  return results;
}

// ---------------------------------------------------------------------------
// Parquet reachability check (client-side — uses fetch)
// ---------------------------------------------------------------------------

/**
 * Issues a HEAD request to verify a parquet file is accessible before
 * DuckDB-Wasm attempts to range-read it.
 *
 * Throws DataUnavailableError with a user-friendly message if the file
 * returns a non-2xx status, so the UI can display a clear explanation
 * instead of a raw DuckDB network error.
 */
export async function checkParquetReachable(
  url: string,
  label: string,
): Promise<void> {
  try {
    const res = await fetch(url, { method: 'HEAD' });
    if (!res.ok) {
      throw new DataUnavailableError(
        `"${label}" data is not available (HTTP ${res.status}). ` +
        `Run the ETL script to generate ${url.split('/').pop() ?? 'the parquet file'}.`,
        label,
        url,
      );
    }
  } catch (err) {
    if (err instanceof DataUnavailableError) throw err;
    throw new DataUnavailableError(
      `"${label}" could not be reached: ${err instanceof Error ? err.message : String(err)}`,
      label,
      url,
    );
  }
}
