/**
 * Scout RAG API — POST /api/scout/rag-query
 * ==========================================
 * Module 26 companion to /api/scout/query.
 *
 * Instead of injecting the full STAC catalog on every query (prompt stuffing),
 * this route does semantic retrieval:
 *   1. Reads the retrieval_index.json produced by Python Exercise 3
 *   2. Embeds the user query using a pure-TS cosine similarity against
 *      the pre-computed embedding vectors in the index
 *   3. Selects the top-K most relevant schema chunks
 *   4. Builds a targeted prompt from only those chunks
 *   5. Returns { sql, provider, usage, retrieved_chunks }
 *
 * Architecture note:
 *   Python owns the embedding pipeline (ChromaDB, sentence-transformers).
 *   Next.js reads the exported JSON index — a flat list of {id, document,
 *   metadata, embedding} objects — and does cosine similarity in plain TypeScript.
 *   No native modules, no Python subprocess. The embedding math is pure arithmetic.
 *
 * To regenerate the index after adding new datasets:
 *   cd src/exercises && uv run python 26-vector-rag/03_onboard_buildings.py
 *   cp 26-vector-rag/output/retrieval_index.json ../../public/data/
 */

import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import { PIPELINE } from '@/lib/scout-pipeline';
import { validateSql, enforceLimitClause } from '@/lib/scout-guards';
import { checkRateLimit } from '@/lib/rate-limit';
import { getLlmAccess } from '@/lib/llm-access';
import {
  type RetrievalIndex,
  retrieveTopK,
  partitionChunks,
  buildRagPrompt,
} from '@/lib/scout-rag';

// ---------------------------------------------------------------------------
// Paths
// ---------------------------------------------------------------------------

// Exercise 3 exports here; we copy to public/data for Next.js to serve/read.
// We check both locations so you don't have to manually copy during dev.
const INDEX_PATHS = [
  path.join(process.cwd(), 'public', 'data', 'retrieval_index.json'),
  path.join(
    process.cwd(),
    'src', 'exercises', '26-vector-rag', 'output', 'retrieval_index.json'
  ),
];

// ---------------------------------------------------------------------------
// Query embedding (via the same API we're calling anyway)
// ---------------------------------------------------------------------------

/**
 * Embed the user query using the configured LLM provider's embedding API.
 *
 * In production you'd use the same sentence-transformer model as Python
 * (served via a FastAPI sidecar or a cloud embedding endpoint). For this
 * tutorial we use OpenAI text-embedding-3-small or a local stub.
 *
 * Note: dimension mismatch with all-MiniLM-L6-v2 (384-dim) would require
 * the same model. For the tutorial, we use a cosine approximation over the
 * keyword overlap when embeddings can't be generated (graceful fallback).
 */
async function embedQuery(query: string): Promise<number[] | null> {
  const provider = (process.env.LLM_PROVIDER ?? 'claude').toLowerCase();

  if (provider === 'openai' && process.env.OPENAI_API_KEY) {
    try {
      const { default: OpenAI } = await import('openai');
      const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
      const response = await client.embeddings.create({
        model: 'text-embedding-3-small',
        input: query,
      });
      return response.data[0].embedding;
    } catch {
      // fall through to keyword scoring
    }
  }

  return null; // triggers keyword fallback below
}

// ---------------------------------------------------------------------------
// LLM callers (same as /api/scout/query)
// ---------------------------------------------------------------------------

async function callLLM(
  systemPrompt: string,
  userQuery: string
): Promise<{ sql: string; provider: string; usage: { input_tokens: number; output_tokens: number } }> {
  const provider = (process.env.LLM_PROVIDER ?? 'claude').toLowerCase();

  if (provider === 'openai') {
    const { default: OpenAI } = await import('openai');
    const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
    const completion = await client.chat.completions.create({
      model: 'gpt-4o',
      max_tokens: 512,
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userQuery },
      ],
    });
    return {
      sql: completion.choices[0].message.content?.trim() ?? '',
      provider: 'openai',
      usage: {
        input_tokens: completion.usage?.prompt_tokens ?? 0,
        output_tokens: completion.usage?.completion_tokens ?? 0,
      },
    };
  }

  const { default: Anthropic } = await import('@anthropic-ai/sdk');
  const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
  const message = await client.messages.create({
    model: 'claude-sonnet-4-6',
    max_tokens: 512,
    system: systemPrompt,
    messages: [{ role: 'user', content: userQuery }],
  });

  return {
    sql: message.content[0].type === 'text' ? message.content[0].text.trim() : '',
    provider: 'claude (rag)',
    usage: {
      input_tokens: message.usage.input_tokens,
      output_tokens: message.usage.output_tokens,
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

  // 1. Parse request
  let query: string;
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
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  // 2. Load retrieval index
  let indexPath: string | null = null;
  for (const p of INDEX_PATHS) {
    if (fs.existsSync(p)) {
      indexPath = p;
      break;
    }
  }

  if (!indexPath) {
    return NextResponse.json(
      {
        error: 'Retrieval index not found.',
        details: [
          'Run: cd src/exercises && uv run python 26-vector-rag/03_onboard_buildings.py',
          'Then copy the output to public/data/retrieval_index.json',
        ].join(' | '),
      },
      { status: 503 }
    );
  }

  let index: RetrievalIndex;
  try {
    index = JSON.parse(fs.readFileSync(indexPath, 'utf-8')) as RetrievalIndex;
  } catch (e) {
    return NextResponse.json(
      { error: 'Failed to parse retrieval index', details: String(e) },
      { status: 500 }
    );
  }

  // 3. Embed query (with graceful fallback to keyword scoring)
  const queryEmbedding = await embedQuery(query);
  const scoringMethod = queryEmbedding ? 'cosine (pre-computed embeddings)' : 'keyword overlap (embedding unavailable)';

  // 4. Retrieve top-K chunks, then partition into used vs filtered
  const topChunks = retrieveTopK(index, queryEmbedding, query, PIPELINE.TOP_K);
  const { used, filtered } = partitionChunks(topChunks, PIPELINE.SIM_THRESHOLD);

  // 5. Build RAG prompt from the chunks that passed the threshold
  const { prompt, retrievedChunks } = buildRagPrompt(used);

  // Check API key before calling LLM
  const provider = (process.env.LLM_PROVIDER ?? 'claude').toLowerCase();
  const apiKey = provider === 'openai' ? process.env.OPENAI_API_KEY : process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    return NextResponse.json(
      {
        error: `Missing API key for provider: ${provider}`,
        details: provider === 'openai'
          ? 'Set OPENAI_API_KEY in your .env.local file.'
          : 'Set ANTHROPIC_API_KEY in your .env.local file.',
      },
      { status: 503 }
    );
  }

  // 6. Call LLM
  try {
    const result = await callLLM(prompt, query);

    // Guard: reject DDL/DML and enforce row limit
    const sqlValidation = validateSql(result.sql);
    if (!sqlValidation.valid) {
      return NextResponse.json(
        { error: 'LLM generated unsafe SQL', details: sqlValidation.reason },
        { status: 422 }
      );
    }
    const safeSql = enforceLimitClause(result.sql);

    return NextResponse.json({
      ...result,
      sql: safeSql,
      retrieved_chunks: retrievedChunks,
      filtered_chunks: filtered,
      pipeline: {
        scoring_method: scoringMethod,
        top_k_fetched: PIPELINE.TOP_K,
        sim_threshold: PIPELINE.SIM_THRESHOLD,
        chunks_used: retrievedChunks.length,
        chunks_filtered: filtered.length,
        index_model: index.model,
        index_exported_at: index.exported_at,
      },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      { error: 'LLM call failed', details: message },
      { status: 502 }
    );
  }
}
