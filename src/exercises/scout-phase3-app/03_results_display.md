# Exercise 3: The Results Display

This guide covers the results panel in `src/app/scout/page.tsx` and the marker
rendering in `src/app/scout/components/ScoutMap.tsx`.

By the end of this exercise you will understand every UI element that appears
after a query completes — markers on the map, hover popups, result counts, SQL
display, the results table, and the mode-specific trace panels.

---

## Map Markers and Hover Popups (ScoutMap.tsx)

Results are rendered as HTML markers — DOM elements positioned on top of the
MapLibre canvas. This is the simplest approach for datasets up to ~5,000 points:
no source/layer pipeline, no tile encoding, just absolute-positioned divs.

### The red dot element

```typescript
const el = document.createElement("div");
el.style.cssText = `
  width: 14px; height: 14px;
  border-radius: 50%;
  background: #ef4444;
  border: 2px solid #fff;
  box-shadow: 0 1px 4px rgba(0,0,0,0.4);
  cursor: pointer;
`;
```

This is a plain CSS red circle. No React — it's created in a callback that runs
inside an async function inside a `useCallback`. Using React's render cycle here
would require converting each result to a React element and rendering it via a
portal, which adds complexity for no benefit at this scale.

### The popup

```typescript
const popup = new maplibregl.Popup({
  closeButton: false,
  offset: 10,
}).setHTML(`
  <div style="font-size:13px;line-height:1.5">
    <strong>${row.name ?? "Unknown"}</strong><br/>
    <span style="color:#6b7280">${row.category ?? ""}</span>
  </div>
`);
```

`closeButton: false` prevents the default ×-button from appearing on hover — the
popup is driven entirely by `mouseenter`/`mouseleave`:

```typescript
el.addEventListener("mouseenter", () => marker.togglePopup());
el.addEventListener("mouseleave", () => {
  if (popup.isOpen()) marker.togglePopup();
});
```

The second guard (`if (popup.isOpen())`) prevents calling `togglePopup()` when
the mouse leaves without the popup having opened — which would open it instead
of closing it.

### Clearing old markers

Before adding new markers, the previous set is removed:

```typescript
markersRef.current.forEach((m) => m.remove());
markersRef.current = [];
```

`markersRef` is a ref (not state) because updating it must not trigger a
re-render — it's a side-effect bookkeeping array, not UI-driving data.

### Map bounds fitting

After rendering markers, the map fits to the result extent:

```typescript
const bounds = new maplibregl.LngLatBounds();
features.forEach((f) => {
  bounds.extend(coords as [number, number]);
});
map.fitBounds(bounds, { padding: 60, maxZoom: 16 });
```

`maxZoom: 16` prevents the map from zooming in too far when there's only one
result (a single café doesn't need to fill the screen).

---

## The SQL Rewrite (ScoutMap.tsx)

The LLM generates SQL that references `FROM places` — a table that doesn't exist
in the browser. DuckDB-Wasm reads from URLs, not tables. Two rewrites happen
before execution:

```typescript
// 1. Strip LOAD statements — extensions already loaded during init
const cleanedSql = sql.replace(/LOAD\s+\w+;\s*/gi, "");

// 2. Rewrite FROM places → FROM read_parquet(URL)
const parquetUrl = `${window.location.origin}/data/sf_places.parquet`;
const rewrittenSql = cleanedSql.replace(
  /\bFROM\s+places\b/gi,
  `FROM read_parquet('${parquetUrl}')`,
);
```

The `\b` word boundary ensures `FROM places_cache` wouldn't be rewritten. The
`/gi` flags make it case-insensitive and global (handles multiple occurrences,
e.g., in a subquery).

`window.location.origin` gives `http://localhost:3000` in dev and the deployed
URL in production — the GeoParquet file is served from `public/data/`, so
Next.js's static file server handles it at `/data/sf_places.parquet`.

---

## The Results Panel (page.tsx)

The bottom panel renders conditionally: nothing appears until the first query.

```typescript
{
  (queryState.sql || queryState.error) && (
    <div className="mt-2 text-sm">
      {/* ... all result sub-panels */}
    </div>
  );
}
```

### Result count

```typescript
{
  queryState.resultCount !== null && (
    <span className={`font-medium ${cfg.countColor}`}>
      Found {queryState.resultCount.toLocaleString()} places
    </span>
  );
}
```

`toLocaleString()` formats large numbers with commas. `cfg.countColor` picks the
mode's color: blue for stuffing, emerald for rag, violet for agent.
`resultCount` starts as `null` (not zero) so "Found 0 places" doesn't flash
before results arrive.

### Agent: Reasoning trace

```typescript
{
  mode === "agent" && queryState.reasoningTrace.length > 0 && (
    <details open>
      <summary>Reasoning trace: N tool calls (M total tokens)</summary>
      {queryState.reasoningTrace.map((call) => (
        <details key={call.step} className="... bg-violet-50">
          <summary>
            <StepBadge>{call.step}</StepBadge>
            <span>{call.tool}</span>
            <span>{call.elapsed_ms}ms</span>
            <span>{truncate(Object.values(call.input)[0])}</span>
          </summary>
          <pre>Input: {JSON.stringify(call.input, null, 2)}</pre>
          <pre>Output: {call.output}</pre>
        </details>
      ))}
      <TokenSummary>{agentUsage}</TokenSummary>
    </details>
  );
}
```

The nested `<details>` pattern (one outer for the whole trace, one per call)
lets you scan the trace summary without expanding every tool call's
input/output. `open` on the outer `<details>` means it starts expanded — the
agent reasoning trace is the main educational artifact of the starting of scout
module.

### RAG: Retrieved and filtered chunks

Two separate panels show what the vector search returned:

1. **Retrieved chunks** (green) — chunks that scored above the similarity
   threshold and were included in the LLM prompt
2. **Filtered chunks** (amber) — chunks that were fetched but scored below the
   threshold; shown so you can see what was _rejected_

The similarity score badge on each chunk is the cosine similarity between the
query embedding and the chunk embedding. Values near 1.0 are high-confidence
matches; values below ~0.3 usually indicate the chunk is about a different
topic.

### SQL collapsible

```typescript
<details className="mt-1">
  <summary className="cursor-pointer text-gray-400 hover:text-gray-600 text-xs">
    Show generated SQL
  </summary>
  <pre className="... font-mono text-gray-700">
    {queryState.sql}
  </pre>
</details>;
```

This is collapsed by default. As a learner, you should open it on every query to
read what the LLM generated. As a portfolio reviewer, it shows that the app is
transparent about what the AI produced.

### Results table

```typescript
<details className="mt-1">
  <summary>Inspect results ({queryState.results.length} rows)</summary>
  <table>
    <thead>{/* #, name, category, lon, lat */}</thead>
    <tbody>
      {queryState.results.slice(0, 50).map((r, i) => (
        <tr key={i}>
          <td>{i + 1}</td>
          <td>{r.name}</td>
          <td>{r.category}</td>
          <td>{r.lon.toFixed(6)}</td>
          <td>{r.lat.toFixed(6)}</td>
        </tr>
      ))}
    </tbody>
  </table>
  {results.length > 50 && <p>Showing first 50 of {results.length}</p>}
</details>;
```

The table is capped at 50 displayed rows (`slice(0, 50)`) — showing 200 rows of
DOM elements slows scrolling noticeably. The max-h-48 + overflow-auto on the
container makes it scrollable without expanding to fill the page.

---

## What to Observe

1. **Hover a marker** — the popup appears on `mouseenter` and disappears on
   `mouseleave`. Click the marker — the popup stays open (it's a MapLibre popup,
   not a hover tooltip). This is because `togglePopup()` also fires on click by
   default; you'd need `closeOnClick: false` on the Popup to prevent it.

2. **Open "Show generated SQL"** on several queries — compare what the LLM
   generates for "Show me hospitals" vs. "Find ERs". Do both produce the same
   category value? This is the closed-vocabulary constraint in action.

3. **Open "Inspect results"** and compare lon/lat values against the map. Pick a
   row at `lon: -122.42, lat: 37.77` — that should be roughly in the Castro /
   Upper Market area. This sanity-check habit (coordinates → place on map) is
   essential when working with LLM-generated spatial queries.

4. **Run a query that returns 0 results** — e.g., "Show me ski resorts in SF".
   The map doesn't move, the result count shows "Found 0 places", and the SQL is
   still visible. The UX degrades gracefully rather than silently failing.

5. **Switch to agent mode and run a multi-step query** — watch the reasoning
   trace appear. Notice the `elapsed_ms` field on each tool call. Which tool
   takes the longest? Is it the LLM turn or the `execute_sql` tool? This is
   where latency optimization conversations start as a product manager: if
   `execute_sql` dominates, the bottleneck is DuckDB initialization or query
   complexity. If the LLM turn dominates, the bottleneck is tokens-per-second.

---

The actual implementations are at:

- `src/app/scout/components/ScoutMap.tsx` (marker rendering, SQL rewrite)
- `src/app/scout/page.tsx` (results panel, mode-specific trace displays)
