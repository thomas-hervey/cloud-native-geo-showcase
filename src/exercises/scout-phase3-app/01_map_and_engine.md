# Exercise 1: Initialize the Map and DuckDB Engine

This guide walks through `src/app/scout/components/ScoutMap.tsx` — the component
that owns the two long-lived browser objects that everything else depends on.

---

## What You're Building

Before any query can run, two things must be initialized:

1. **MapLibre GL JS** — renders the basemap tiles and handles pan/zoom
2. **DuckDB-Wasm** — the in-browser columnar database that executes SQL against
   GeoParquet files via HTTP range requests

Neither can be initialized at import time (they both need the browser environment
and the DOM). Both run inside a React `useEffect` that fires once on mount.

---

## The DuckDB-Wasm Bundle Problem

The first challenge with DuckDB-Wasm in Next.js / Turbopack is the **WASM
bundling problem**. DuckDB-Wasm ships multiple bundles (for different browser
feature sets) and spawns Web Workers. Webpack/Turbopack doesn't know how to
handle these — it tries to inline them, which breaks at runtime.

The solution used in this project: **CDN-hosted bundles with a blob Worker URL**.

```typescript
async function initDuckDB() {
  const duckdb = await import('@duckdb/duckdb-wasm');

  // Let DuckDB select the right bundle for this browser (MVP, EH, or COOP)
  const JSDELIVR_BUNDLES = duckdb.getJsDelivrBundles();
  const bundle = await duckdb.selectBundle(JSDELIVR_BUNDLES);

  // Trick: wrap the CDN worker script in a local blob URL.
  // This tells the browser to load the worker from jsDelivr — not from
  // Next.js's dev server, where Turbopack would intercept and mangle it.
  const worker_url = URL.createObjectURL(
    new Blob([`importScripts("${bundle.mainWorker}");`], {
      type: 'text/javascript',
    })
  );

  const worker = new Worker(worker_url);
  const logger = new duckdb.ConsoleLogger();
  const db = new duckdb.AsyncDuckDB(logger, worker);
  await db.instantiate(bundle.mainModule, bundle.pthreadWorker);

  URL.revokeObjectURL(worker_url);  // Clean up the temporary blob URL

  const conn = await db.connect();

  // Load extensions — must happen before any spatial or HTTP queries
  await conn.query('INSTALL spatial; LOAD spatial;');
  await conn.query('INSTALL httpfs; LOAD httpfs;');

  return { db, conn };
}
```

**Why `getJsDelivrBundles()`?** DuckDB-Wasm ships three bundles: MVP (broadest
compatibility), EH (exception handling), and COOP (Cross-Origin Isolated).
`selectBundle()` probes browser capabilities and picks the best one.

**Why the blob URL?** The worker script needs to load WASM from jsDelivr's CDN.
If we pass the CDN URL directly to `new Worker(...)`, the browser blocks it as
a cross-origin worker. Wrapping it in `importScripts()` inside a blob URL runs
it as a same-origin worker that then reaches out to the CDN — this pattern
bypasses both the CORS block and Turbopack's module transformation.

---

## The Dual-Readiness Gate

MapLibre and DuckDB initialize concurrently, but the parent needs to know when
**both** are ready before it can accept queries. A single boolean flag for each,
closed over by a shared `maybeSignalReady` function:

```typescript
let mapLoaded = false;
let duckdbReady = false;

const maybeSignalReady = () => {
  if (mapLoaded && duckdbReady) {
    setEngineStatus('Ready');
    onReady(executeQuery);   // Hand the executeQuery function to the parent
  }
};

map.on('load', () => {
  mapLoaded = true;
  maybeSignalReady();
});

const instance = await initDuckDB();
duckdbRef.current = instance;
duckdbReady = true;
if (!mapLoaded) setEngineStatus('Waiting for map...');
maybeSignalReady();
```

**Why gate on `map.on('load')` instead of `new Map()`?**
The `Map` constructor returns immediately — it's synchronous. The map _object_
exists, but the style tiles haven't loaded. Any call to `addSource` or `addLayer`
before the `load` event fires will silently fail. Gating on the event guarantees
the map is renderable.

**The status progression**: `Initializing...` → `Loading DuckDB-Wasm...` →
`Waiting for map...` (if DuckDB wins the race) → `Ready` → `Querying...` →
`Ready — N results`.

---

## The `useEffect` Cleanup

Because `ScoutMap` runs in strict mode during development, React mounts and
unmounts the component twice. Without cleanup, you'd initialize two maps and two
DuckDB instances. The `cancelled` flag and cleanup function handle this:

```typescript
useEffect(() => {
  let cancelled = false;
  let mapInstance = null;

  async function init() {
    // ... all async init work
    if (cancelled) return;  // Check after every await
    // ...
  }

  init();

  return () => {
    cancelled = true;
    markersRef.current.forEach((m) => m.remove());
    mapInstance?.remove();    // Detaches MapLibre from the DOM
    duckdbRef.current?.conn.close();
  };
}, []);  // Empty deps — runs once on mount
```

---

## The Status Badge

The green/yellow/red badge in the top-left of the map communicates engine state:

```tsx
<div className="absolute top-3 left-3 bg-white/90 ...">
  <span className={`w-2 h-2 rounded-full ${
    engineStatus === 'Ready' || engineStatus.includes('results')
      ? 'bg-green-500'
      : engineStatus.includes('error')
      ? 'bg-red-500'
      : 'bg-yellow-500 animate-pulse'  // Any other state = loading
  }`} />
  <span>{engineStatus}</span>
</div>
```

The badge is absolutely positioned (`top-3 left-3`) over the map div — MapLibre
navigation controls are in the top-right, so they don't overlap.

---

## What to Observe

1. **Open the browser console** and load `/scout`. You'll see the sequence:
   ```
   [Scout] Map style loaded
   [Scout] DuckDB-Wasm initialized
   [Scout] Both map and DuckDB ready
   ```
   The order of the first two may vary — DuckDB usually wins because jsDelivr's
   CDN is fast and maplibre has to fetch tile JSON + fonts.

2. **Network tab → filter by "duckdb"** — you'll see the `.wasm` and worker
   `.js` files loading from `cdn.jsdelivr.net`. This confirms the CDN strategy
   is working. No WASM blob appears in the Next.js dev server requests.

3. **Performance tab → record page load** — you'll see a distinct orange spike
   when the Wasm binary compiles. This is the 1–3 second "engine init" window.
   Check which thread it's on — it should be a Worker thread, not the main
   thread, which is why the UI remains responsive during compilation.

4. **Tile style URL**: `https://tiles.openfreemap.org/styles/liberty` — this is
   the free tile provider used instead of Mapbox. No token required. Open it in
   the browser — you'll see a MapLibre style JSON with source definitions.

---

The actual implementation is at `src/app/scout/components/ScoutMap.tsx`.
Open it side-by-side with this guide.
