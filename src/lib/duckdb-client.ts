/**
 * duckdb-client — shared DuckDB-Wasm initialization
 * ===================================================
 * Single source of truth for initializing a DuckDB-Wasm instance with the
 * CDN-hosted JsDelivr bundles. Previously duplicated in ScoutMap and LabMap.
 *
 * Usage:
 *   import { initDuckDB } from '@/lib/duckdb-client';
 *   const { db, conn } = await initDuckDB();
 */

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type DuckDBInstance = { db: any; conn: any; dispose: () => Promise<void> };

export async function initDuckDB(): Promise<DuckDBInstance> {
  const duckdb = await import('@duckdb/duckdb-wasm');

  // CDN-hosted bundles — avoids Webpack/Turbopack WASM bundling issues
  const JSDELIVR_BUNDLES = duckdb.getJsDelivrBundles();
  const bundle = await duckdb.selectBundle(JSDELIVR_BUNDLES);

  const worker_url = URL.createObjectURL(
    new Blob([`importScripts("${bundle.mainWorker}");`], {
      type: 'text/javascript',
    })
  );

  const worker = new Worker(worker_url);
  const logger = new duckdb.ConsoleLogger();
  const db = new duckdb.AsyncDuckDB(logger, worker);
  await db.instantiate(bundle.mainModule, bundle.pthreadWorker);

  URL.revokeObjectURL(worker_url);

  const conn = await db.connect();

  // Load extensions — spatial for geometry, httpfs for HTTP range requests
  await conn.query('INSTALL spatial; LOAD spatial;');
  await conn.query('INSTALL httpfs; LOAD httpfs;');

  let disposed = false;
  const dispose = async () => {
    if (disposed) return;
    disposed = true;
    try {
      try { await conn.close(); } catch { /* ignore */ }
      try { await db.terminate(); } catch { /* ignore */ }
    } finally {
      worker.terminate();
    }
  };

  return { db, conn, dispose };
}
