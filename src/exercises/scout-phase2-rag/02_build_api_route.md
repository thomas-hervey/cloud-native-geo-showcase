# Exercise 2: Build the Next.js API Route

This guide walks through `src/app/api/scout/query/route.ts` — the single
server-side component of the entire Scout application.

The route you're building does exactly one thing: translate a natural language
string into a DuckDB SQL string. That's the whole job.

---

## What the Route Needs to Do

```text
Client                    Server (route.ts)               LLM API
  │                            │                              │
  │  POST /api/scout/query     │                              │
  │  { "query": "coffee shops  │                              │
  │    near Dolores Park" }    │                              │
  │ ─────────────────────────► │                              │
  │                            │  1. Read STAC item JSON      │
  │                            │  2. Build system prompt      │
  │                            │  3. Call LLM ─────────────► │
  │                            │                 SQL string ◄─│
  │                            │  4. Return response          │
  │ ◄───────────────────────── │                              │
  │  { sql, provider, usage }  │
```

## Request and Response Shapes

```typescript
// POST body
{
  query: string;
}

// Success response
{
  sql: string; // e.g. "LOAD spatial;\nSELECT ..."
  provider: string; // "claude" | "openai"
  usage: {
    input_tokens: number;
    output_tokens: number;
  }
}

// Error response
{
  error: string; // human-readable message
  details: string; // technical details for debugging
}
```

## The STAC Item Path

The route reads the STAC item JSON from the filesystem at request time. In
production you'd put this on S3 and cache it — but for learning, the explicit
file read makes the data flow visible.

```typescript
import path from "path";

const STAC_ITEM_PATH = path.join(
  process.cwd(),
  "src",
  "exercises",
  "23-scout-etl",
  "output",
  "stac",
  "sf-places",
  "sf-places-2026",
  "sf-places-2026.json",
);
```

## The System Prompt Builder

This is the same logic as `01_test_prompt.py`, ported to TypeScript.

```typescript
interface StacItem {
  properties: {
    "scout:schema": Record<string, string>;
    "scout:categories": string[];
    "scout:table_name": string;
    "scout:duckdb_notes": string;
    "scout:row_count": number;
  };
}

function buildSystemPrompt(item: StacItem): string {
  const { properties: p } = item;
  const schemaBlock = Object.entries(p["scout:schema"])
    .map(([col, desc]) => `  ${col.padEnd(12)} -- ${desc}`)
    .join("\n");
  const categoryList = p["scout:categories"].join(", ");

  return `You are a SQL query generator for a DuckDB database.
The database contains a single table named '${p["scout:table_name"]}' with ${
    p["scout:row_count"].toLocaleString()
  } rows.

## Schema
${schemaBlock}

## Valid category values
${categoryList}

## DuckDB spatial notes
${p["scout:duckdb_notes"]}

## Output rules
- Return ONLY a valid DuckDB SQL SELECT statement. No explanation, no markdown.
- Always include: LOAD spatial; as the first statement.
- Use ST_DWithin for proximity queries. Default radius: 0.005 degrees (~500m).
- LIMIT results to 200 rows unless specified otherwise.
- Never generate INSERT, UPDATE, DELETE, DROP, or CREATE.`;
}
```

## The Anthropic Call

```typescript
import Anthropic from "@anthropic-ai/sdk";

async function callClaude(systemPrompt: string, userQuery: string) {
  const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
  const message = await client.messages.create({
    model: "claude-sonnet-4-6",
    max_tokens: 512,
    system: systemPrompt,
    messages: [{ role: "user", content: userQuery }],
  });
  const sql = message.content[0].type === "text"
    ? message.content[0].text.trim()
    : "";
  return {
    sql,
    provider: "claude",
    usage: {
      input_tokens: message.usage.input_tokens,
      output_tokens: message.usage.output_tokens,
    },
  };
}
```

## The OpenAI Call

```typescript
import OpenAI from "openai";

async function callOpenAI(systemPrompt: string, userQuery: string) {
  const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
  const completion = await client.chat.completions.create({
    model: "gpt-4o",
    max_tokens: 512,
    messages: [
      { role: "system", content: systemPrompt },
      { role: "user", content: userQuery },
    ],
  });
  const sql = completion.choices[0].message.content?.trim() ?? "";
  return {
    sql,
    provider: "openai",
    usage: {
      input_tokens: completion.usage?.prompt_tokens ?? 0,
      output_tokens: completion.usage?.completion_tokens ?? 0,
    },
  };
}
```

## The POST Handler

```typescript
import { NextRequest, NextResponse } from "next/server";
import fs from "fs";

export async function POST(request: NextRequest) {
  // 1. Parse request body
  let query: string;
  try {
    const body = await request.json();
    query = body.query;
    if (!query || typeof query !== "string") {
      return NextResponse.json(
        { error: "Missing required field: query (string)" },
        { status: 400 },
      );
    }
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  // 2. Load STAC item
  let item: StacItem;
  try {
    const raw = fs.readFileSync(STAC_ITEM_PATH, "utf-8");
    item = JSON.parse(raw);
  } catch {
    return NextResponse.json(
      {
        error: "STAC catalog not found",
        details:
          "Run src/exercises/23-scout-etl/03_build_stac_catalog.py first.",
      },
      { status: 503 },
    );
  }

  // 3. Build prompt and call LLM
  const systemPrompt = buildSystemPrompt(item);
  const provider = (process.env.LLM_PROVIDER ?? "claude").toLowerCase();

  try {
    const result = provider === "openai"
      ? await callOpenAI(systemPrompt, query)
      : await callClaude(systemPrompt, query);

    return NextResponse.json(result);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      { error: "LLM call failed", details: message },
      { status: 502 },
    );
  }
}
```

## Testing with curl

Once `pnpm dev` is running:

```bash
# Test with Anthropic
LLM_PROVIDER=claude ANTHROPIC_API_KEY=sk-ant-... pnpm dev

curl -s -X POST http://localhost:3000/api/scout/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Show me coffee shops near Dolores Park"}' | jq .
```

Expected response shape:

```json
{
  "sql": "LOAD spatial;\nSELECT id, name, category, lat, lon\n...",
  "provider": "claude",
  "usage": { "input_tokens": 1842, "output_tokens": 63 }
}
```

## Things to Observe

- **input_tokens is large** — the system prompt with all 240+ categories is the
  bulk of your cost. Every query pays this fixed overhead. This is the
  prompt-stuffing cost the first scout module describes.
- **The `provider` field** — swap `LLM_PROVIDER=openai` and run the same query.
  Both should produce SQL that uses valid column names and category values.
  Which handles "show me sushi restaurants" better?
- **The contract shape** — `{ sql, provider, usage }` is the exact shape the
  scout llm frontend will consume. If you change it, the frontend breaks.
- **The LOAD spatial; prefix** — DuckDB-Wasm in the browser needs this before
  any ST_* function. The LLM is instructed to include it; check that it always
  does.

---

The actual implementation lives in `src/app/api/scout/query/route.ts`. Open it
side-by-side with this guide as you read the code.
