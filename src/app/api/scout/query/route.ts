/**
 * Scout API — POST /api/scout/query
 * ==================================
 * Translates a natural language query into a DuckDB SQL SELECT statement
 * using an LLM informed by the Scout STAC catalog.
 *
 * Module 24, Exercise 2 — see the guided walkthrough:
 *   src/exercises/24-scout-backend/02_build_api_route.md
 *
 * Environment variables:
 *   LLM_PROVIDER     "claude" (default) | "openai"
 *   ANTHROPIC_API_KEY  required when LLM_PROVIDER=claude
 *   OPENAI_API_KEY     required when LLM_PROVIDER=openai
 */

import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import { validateSql, enforceLimitClause } from '@/lib/scout-guards';
import { checkRateLimit } from '@/lib/rate-limit';
import { getLlmAccess } from '@/lib/llm-access';
import { createClient } from '@/lib/supabase/server';
import { detectProvider, validateKeyForProvider } from '@/lib/api-key-utils';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface StacItem {
  properties: {
    'scout:schema': Record<string, string>;
    'scout:categories': string[];
    'scout:table_name': string;
    'scout:duckdb_notes': string;
    'scout:row_count': number;
  };
}

interface QueryResult {
  sql: string;
  provider: string;
  usage: {
    input_tokens: number;
    output_tokens: number;
  };
}

// ---------------------------------------------------------------------------
// STAC catalog path
// ---------------------------------------------------------------------------

// Reads from the filesystem at request time — makes the data flow explicit.
// For production: move this to an S3 URL and add caching.
const STAC_ITEM_PATH = path.join(
  process.cwd(),
  'src', 'exercises', '23-scout-etl', 'output', 'stac',
  'sf-places', 'sf-places-2026', 'sf-places-2026.json'
);

// ---------------------------------------------------------------------------
// Prompt builder
// ---------------------------------------------------------------------------

function buildSystemPrompt(item: StacItem): string {
  const { properties: p } = item;

  const schemaBlock = Object.entries(p['scout:schema'])
    .map(([col, desc]) => `  ${col.padEnd(12)} -- ${desc}`)
    .join('\n');

  const categoryList = p['scout:categories'].join(', ');

  return `You are a SQL query generator for a DuckDB database.
The database contains a single table named '${p['scout:table_name']}' with ${p['scout:row_count'].toLocaleString()} rows of San Francisco points of interest from Overture Maps.

## Schema

${schemaBlock}

## Valid category values

Use ONLY the following values for the \`category\` column — no other values exist in the data. If the user asks for something not on this list, choose the closest match or combine multiple valid categories with OR.

${categoryList}

## DuckDB spatial notes

${p['scout:duckdb_notes']}

## Output rules

- Return ONLY a valid DuckDB SQL SELECT statement. No explanation, no markdown code fences, no commentary.
- Always include: LOAD spatial; as the first statement on its own line.
- Use ST_DWithin for proximity queries. Default radius: 0.005 degrees (~500m at SF latitude).
- Always SELECT id, name, category, lat, lon at minimum.
- LIMIT results to 200 rows unless the user specifies otherwise.
- Never generate INSERT, UPDATE, DELETE, DROP, or CREATE statements.
- If the query is ambiguous, make a reasonable spatial assumption and proceed.`;
}

// ---------------------------------------------------------------------------
// LLM callers
// ---------------------------------------------------------------------------

async function callClaude(
  systemPrompt: string,
  userQuery: string,
  apiKey: string
): Promise<QueryResult> {
  const { default: Anthropic } = await import('@anthropic-ai/sdk');
  const client = new Anthropic({ apiKey });

  const message = await client.messages.create({
    model: 'claude-sonnet-4-6',
    max_tokens: 512,
    system: systemPrompt,
    messages: [{ role: 'user', content: userQuery }],
  });

  const sql =
    message.content[0].type === 'text' ? message.content[0].text.trim() : '';

  return {
    sql,
    provider: 'claude',
    usage: {
      input_tokens: message.usage.input_tokens,
      output_tokens: message.usage.output_tokens,
    },
  };
}

async function callOpenAI(
  systemPrompt: string,
  userQuery: string,
  apiKey: string
): Promise<QueryResult> {
  const { default: OpenAI } = await import('openai');
  const client = new OpenAI({ apiKey });

  const completion = await client.chat.completions.create({
    model: 'gpt-4o',
    max_tokens: 512,
    messages: [
      { role: 'system', content: systemPrompt },
      { role: 'user', content: userQuery },
    ],
  });

  const sql = completion.choices[0].message.content?.trim() ?? '';

  return {
    sql,
    provider: 'openai',
    usage: {
      input_tokens: completion.usage?.prompt_tokens ?? 0,
      output_tokens: completion.usage?.completion_tokens ?? 0,
    },
  };
}

// ---------------------------------------------------------------------------
// POST handler
// ---------------------------------------------------------------------------

export async function POST(request: NextRequest) {
  // 0. Rate limit check
  const ip = request.headers.get("x-forwarded-for") ?? "127.0.0.1";
  if (!checkRateLimit(ip)) {
    return NextResponse.json(
      { error: "Too many requests. Please try again later." },
      { status: 429 }
    );
  }

  // LLM spend gate: must run before any API key is read or client constructed.
  const llmAccess = await getLlmAccess();
  if (llmAccess.mode !== 'live') {
    return NextResponse.json({ error: 'live_llm_disabled', mode: 'replay' }, { status: 403 });
  }

  // 1. Parse and validate request body
  let query: string;
  let bodyApiKey: string | undefined;
  let bodyProvider: 'claude' | 'openai' | undefined;
  try {
    const body = await request.json();
    query = body?.query;
    if (!query || typeof query !== 'string' || query.trim().length === 0) {
      return NextResponse.json(
        { error: 'Missing or empty required field: query (string)' },
        { status: 400 }
      );
    }
    query = query.trim();
    bodyApiKey = typeof body?.apiKey === 'string' ? body.apiKey : undefined;
    bodyProvider =
      body?.provider === 'openai' ? 'openai' : body?.provider === 'claude' ? 'claude' : undefined;
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  // 2. Load STAC item from filesystem
  let item: StacItem;
  try {
    const raw = fs.readFileSync(STAC_ITEM_PATH, 'utf-8');
    item = JSON.parse(raw) as StacItem;
  } catch {
    return NextResponse.json(
      {
        error: 'STAC catalog not found.',
        details:
          'Run src/exercises/23-scout-etl/03_build_stac_catalog.py first ' +
          'to generate the catalog that this route reads.',
      },
      { status: 503 }
    );
  }

  // 3. Build system prompt from STAC metadata
  const systemPrompt = buildSystemPrompt(item);

  // 4. Resolve API key and provider (admin bypass or BYOK)
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  const isAdmin = user?.app_metadata?.role === 'super-admin';

  let resolvedProvider: string;
  let resolvedApiKey: string;

  if (isAdmin) {
    // Admin may pass a provider preference from the UI toggle; fall back to env var
    resolvedProvider = bodyProvider ?? (process.env.LLM_PROVIDER ?? 'claude').toLowerCase();
    resolvedApiKey = (resolvedProvider === 'openai'
      ? process.env.OPENAI_API_KEY
      : process.env.ANTHROPIC_API_KEY) ?? '';
    if (!resolvedApiKey) {
      return NextResponse.json(
        { error: `Missing server API key for provider: ${resolvedProvider}` },
        { status: 503 }
      );
    }
  } else if (bodyApiKey) {
    const detectedProvider = detectProvider(bodyApiKey);
    if (detectedProvider === 'invalid') {
      return NextResponse.json(
        { error: 'Invalid API key format. Key must start with sk-ant-api03- (Anthropic) or sk- (OpenAI).' },
        { status: 400 }
      );
    }
    if (bodyProvider && bodyProvider !== detectedProvider) {
      const validation = validateKeyForProvider(bodyApiKey, bodyProvider);
      return NextResponse.json({ error: validation.error }, { status: 400 });
    }
    resolvedProvider = detectedProvider;
    resolvedApiKey = bodyApiKey;
  } else {
    return NextResponse.json(
      {
        error: 'API key required',
        details: 'Provide an Anthropic or OpenAI API key in the request body as { apiKey, provider }.',
      },
      { status: 503 }
    );
  }

  try {
    const result =
      resolvedProvider === 'openai'
        ? await callOpenAI(systemPrompt, query, resolvedApiKey)
        : await callClaude(systemPrompt, query, resolvedApiKey);

    // Guard: reject DDL/DML and enforce row limit
    const sqlValidation = validateSql(result.sql);
    if (!sqlValidation.valid) {
      return NextResponse.json(
        { error: 'LLM generated unsafe SQL', details: sqlValidation.reason },
        { status: 422 }
      );
    }
    const safeSql = enforceLimitClause(result.sql);

    return NextResponse.json({ ...result, sql: safeSql });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      {
        error: `LLM call failed (provider: ${resolvedProvider})`,
        details: message,
      },
      { status: 502 }
    );
  }
}
