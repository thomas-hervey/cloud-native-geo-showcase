# Exercise 2: Build the ChatBar and Wire the Query Loop

This guide walks through `src/app/scout/components/ChatBar.tsx` and how it
connects to `ScoutMap.tsx` via the `onSqlReceived` callback in `page.tsx`.

---

## What ChatBar Does

`ChatBar` is a controlled input component with no map or database knowledge. Its
only job is:

1. Accept a text query from the user
2. POST it to the right API endpoint for the current mode
3. Receive the SQL (and any mode-specific metadata)
4. Pass that SQL up to the parent via `onSqlReceived`

The parent (`page.tsx`) holds the `executeQuery` function from `ScoutMap` and
forwards the SQL into DuckDB. `ChatBar` never touches DuckDB directly — this is
the clean separation the module describes.

---

## The Three-Mode Architecture

The biggest design decision in `ChatBar` is that it supports three distinct
modes, each with a different API endpoint and a different response shape:

```typescript
const ENDPOINT: Record<"stuffing" | "rag" | "agent", string> = {
  stuffing: "/api/scout/query", // full STAC in prompt
  rag: "/api/scout/rag-query", // vector-retrieved chunks
  agent: "/api/scout/agent-query", // multi-turn tool loop
};
```

Each mode returns a different response shape:

| Mode     | Additional fields                               |
| -------- | ----------------------------------------------- |
| stuffing | `{ sql, provider, usage }`                      |
| rag      | `+ retrieved_chunks, filtered_chunks, pipeline` |
| agent    | `+ reasoning_trace, usage.total_tokens`         |

The `onSqlReceived` callback signature carries all of these as optional fields —
stuffing mode only sets `sql` and `provider`, rag adds chunks, agent adds trace:

```typescript
interface ChatBarProps {
  mode: "stuffing" | "rag" | "agent";
  onSqlReceived: (
    sql: string,
    provider: string,
    retrievedChunks?: RetrievedChunk[],
    filteredChunks?: FilteredChunk[],
    pipeline?: Pipeline,
    reasoningTrace?: ToolCall[],
    agentUsage?: AgentUsage,
  ) => void;
}
```

The submit handler branches on mode to decide what to extract from the response:

```typescript
if (mode === "agent") {
  onSqlReceived(
    data.sql ?? "",
    data.provider,
    undefined,
    undefined,
    undefined, // No RAG fields
    data.reasoning_trace ?? [],
    data.usage,
  );
} else {
  // stuffing and rag both return the same positional args
  // (rag just has populated chunks; stuffing has undefined)
  onSqlReceived(
    data.sql,
    data.provider,
    data.retrieved_chunks,
    data.filtered_chunks,
    data.pipeline,
  );
}
```

---

## Mode-Specific UI

The button color, loading label, and input placeholder all change per mode:

```typescript
const BUTTON_COLOR = {
  stuffing: "bg-blue-600 hover:bg-blue-700",
  rag: "bg-emerald-600 hover:bg-emerald-700",
  agent: "bg-violet-600 hover:bg-violet-700",
};

const LOADING_LABEL = {
  stuffing: "Thinking...",
  rag: "Retrieving...",
  agent: "Reasoning...",
};

const PLACEHOLDER = {
  stuffing: "Ask about places in San Francisco...",
  rag: "Ask about places or buildings in SF... (RAG mode)",
  agent: "Ask a multi-step question — agent will reason across tools",
};
```

This makes the mode change visually obvious: the button turns green when you
switch to RAG, purple when you switch to agent. Colors here match the badge
colors in `page.tsx` and the mode border accent on the panel.

---

## Example Query Chips

The chips below the input are a UX shortcut for demo and testing. They're split
into three tiers with visual differentiation:

```typescript
const BASE_QUERIES = [
  "Show me coffee shops near Dolores Park",
  "Find all parks in the Marina district",
  // ...
];

const RAG_EXTRA_QUERIES = [
  "Find drugstores", // Tests synonym routing (maps to 'pharmacy')
  "Show me places to eat", // Tests semantic category match
];

const AGENT_EXTRA_QUERIES = [
  "Find areas with high coffee shop density but no parks nearby",
  "What neighborhood has the most restaurants?",
  // ...
];
```

The chip color signals which tier the query belongs to:

- Gray chips → work in all modes
- Emerald chips → demonstrate RAG synonym routing (only shown in rag mode)
- Violet chips → require multi-step reasoning (only shown in agent mode)

Clicking a chip sets the input value and re-focuses the input:

```typescript
onClick={() => { setQuery(example); inputRef.current?.focus(); }}
```

---

## Wiring in page.tsx

`page.tsx` holds the `executeQuery` function (provided by `ScoutMap.onReady`)
and the full `QueryState`. It bridges the two:

```typescript
const handleSqlReceived = useCallback(
  async (
    sql,
    provider,
    retrievedChunks,
    filteredChunks,
    pipeline,
    reasoningTrace,
    agentUsage,
  ) => {
    // 1. Update state with API response metadata immediately
    setQueryState((prev) => ({
      ...prev,
      sql,
      provider,
      resultCount: null,
      error: null,
      results: [],
      retrievedChunks: retrievedChunks ?? [],
      // ...
    }));

    // 2. Run the SQL against DuckDB
    if (!executeQuery) {
      setQueryState((prev) => ({
        ...prev,
        error: "DuckDB engine not ready yet.",
      }));
      return;
    }

    try {
      const { count, features } = await executeQuery(sql);
      setQueryState((prev) => ({
        ...prev,
        resultCount: count,
        results: features,
      }));
    } catch (err) {
      setQueryState((prev) => ({ ...prev, error: String(err) }));
    }
  },
  [executeQuery],
);
```

Note the `useCallback` with `[executeQuery]` in the deps array: `executeQuery`
is stored as state (`useState`) because the `ScoutMap.onReady` callback fires
asynchronously after the component mounts. The callback must re-create when
`executeQuery` changes so `handleSqlReceived` always closes over the current
(non-null) reference.

---

## The Mode Toggle

The 3-way toggle in `page.tsx` cycles through modes on click:

```typescript
const MODE_ORDER: Mode[] = ['stuffing', 'rag', 'agent'];
const nextMode = MODE_ORDER[(MODE_ORDER.indexOf(mode) + 1) % MODE_ORDER.length];

<button onClick={() => { setMode(nextMode); resetQueryState(); }}>
```

Switching mode also calls `resetQueryState()` — this clears the previous query's
SQL, chunks, and results so the panel doesn't show stale rag chunks when you
switch to agent mode, or a reasoning trace when you switch back to stuffing.

---

## What to Observe

1. **Network tab — two requests per query**:
   - Request 1: `POST /api/scout/query` (~200–800ms depending on LLM latency)
   - Request 2: `GET /data/sf_places.parquet` with a `Range: bytes=...` header
     Watch the Range header change between queries — DuckDB is fetching
     different byte ranges as it reads different row groups.

2. **Switch modes before running a query** — watch the button color,
   placeholder, and example chips change immediately. No re-mount of `ScoutMap`
   occurs — only `ChatBar` and the panel re-render. The DuckDB instance
   persists.

3. **Try a RAG synonym query**: In rag mode, type "Find drugstores". The
   retrieved chunks panel will show which schema chunks were used in the prompt.
   In stuffing mode, the same query works because the full category list is
   injected — but there's no visibility into why.

4. **Try an agent query**: In agent mode, type "What neighborhood has the most
   restaurants?". Watch the reasoning trace panel: each tool call shows its
   input, output, and elapsed time. The agent may call `execute_sql` once to
   count by category, then again with a refined query.

5. **`executeQuery` is null on the first render** — the `!executeQuery` guard in
   `handleSqlReceived` catches the case where a user submits before DuckDB is
   ready. Try it: if you could submit instantly (before the green badge
   appears), you'd see "DuckDB engine not ready yet." This is the guard.

---

The actual implementations are at:

- `src/app/scout/components/ChatBar.tsx`
- `src/app/scout/page.tsx`

Open them side-by-side with this guide.
