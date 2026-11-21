/**
 * Agentic GIS — Exercise 1: MCP Geospatial Server
 * =====================================================
 * Exposes Scout's geospatial query capabilities as a Model Context Protocol
 * (MCP) server. Any MCP-compatible client — Claude Desktop, Continue.dev,
 * Cursor, or a custom app — can discover and call these tools without any
 * Scout-specific integration code.
 *
 * Tools exposed:
 *   list_datasets      — discover what geospatial data is available
 *   explain_schema     — get column descriptions for a specific dataset
 *   query_places       — natural language → DuckDB SQL (RAG-powered)
 *   get_map_extent     — returns the current SF map viewport bounding box
 *
 * Compare to the non-MCP agent (agent-query/route.ts):
 *   Baseline: Anthropic-specific tool schemas, hard-wired to the Claude SDK
 *   MCP: Standard MCP protocol — the same server works with any LLM client
 *
 * Setup:
 *   1. pnpm add @modelcontextprotocol/sdk zod dotenv  (already done)
 *   2. Ensure .env.local exists at project root with ANTHROPIC_API_KEY
 *
 * Run (standalone — listens on stdio):
 *   cd src/exercises/agentic-gis
 *   npx tsx 01_mcp_server.ts
 *
 * Test with mcp-inspector (opens browser UI):
 *   npx @modelcontextprotocol/inspector npx tsx 01_mcp_server.ts
 *
 * Add to Claude Desktop (~/Library/Application Support/Claude/claude_desktop_config.json):
 *   {
 *     "mcpServers": {
 *       "scout-geo": {
 *         "command": "npx",
 *         "args": ["tsx", "/abs/path/to/src/exercises/agentic-gis/01_mcp_server.ts"],
 *         "env": { "ANTHROPIC_API_KEY": "sk-ant-..." }
 *       }
 *     }
 *   }
 */

import { config } from 'dotenv';
import path from 'path';
import fs from 'fs';

// Load .env.local from project root (3 dirs up: agentic-gis → exercises → src → root)
const projectRoot = path.resolve(__dirname, '..', '..', '..');
config({ path: path.join(projectRoot, '.env.local') });
config({ path: path.join(__dirname, '.env') }); // local override wins

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import Anthropic from '@anthropic-ai/sdk';

// ---------------------------------------------------------------------------
// Types (mirror of src/app/api/scout/rag-query/route.ts)
// ---------------------------------------------------------------------------

interface IndexDocument {
  id: string;
  document: string;
  metadata: Record<string, string | number | boolean | null>;
  embedding: number[];
}

interface RetrievalIndex {
  model: string;
  collection: string;
  exported_at: string;
  num_documents: number;
  documents: IndexDocument[];
}

// ---------------------------------------------------------------------------
// Configuration (mirrors src/lib/scout-pipeline.ts constants)
// ---------------------------------------------------------------------------

const TOP_K = 5;
const SIM_THRESHOLD = 0.05;

// ---------------------------------------------------------------------------
// Index loading
// ---------------------------------------------------------------------------

/**
 * Loads retrieval_index.json from public/data/ (primary) or the Vector RAG
 * exercise output (fallback — useful during dev before you run `pnpm dev`).
 */
function loadRetrievalIndex(): RetrievalIndex {
  const candidatePaths = [
    path.join(projectRoot, 'public', 'data', 'retrieval_index.json'),
    path.join(projectRoot, 'src', 'exercises', 'vector-rag', 'output', 'retrieval_index.json'),
  ];
  for (const p of candidatePaths) {
    if (fs.existsSync(p)) {
      return JSON.parse(fs.readFileSync(p, 'utf-8')) as RetrievalIndex;
    }
  }
  throw new Error(
    'retrieval_index.json not found. Run the Vector RAG onboarding exercise first:\n' +
    '  cd src/exercises && uv run python vector-rag/03_onboard_buildings.py'
  );
}

// ---------------------------------------------------------------------------
// Cosine similarity (pure TypeScript — copied from rag-query/route.ts)
// ---------------------------------------------------------------------------

function dotProduct(a: number[], b: number[]): number {
  let sum = 0;
  for (let i = 0; i < a.length; i++) sum += a[i] * b[i];
  return sum;
}

function magnitude(v: number[]): number {
  return Math.sqrt(v.reduce((s, x) => s + x * x, 0));
}

function cosineSimilarity(a: number[], b: number[]): number {
  const magA = magnitude(a);
  const magB = magnitude(b);
  if (magA === 0 || magB === 0) return 0;
  return dotProduct(a, b) / (magA * magB);
}

// ---------------------------------------------------------------------------
// Keyword similarity (fallback when embeddings are unavailable)
// ---------------------------------------------------------------------------

function keywordSimilarity(query: string, document: string): number {
  const queryTokens = new Set(query.toLowerCase().split(/\W+/).filter(Boolean));
  const docTokens = document.toLowerCase().split(/\W+/).filter(Boolean);
  let hits = 0;
  for (const token of docTokens) {
    if (queryTokens.has(token)) hits++;
  }
  return queryTokens.size > 0 ? hits / queryTokens.size : 0;
}

// ---------------------------------------------------------------------------
// Top-K retrieval (copied from rag-query/route.ts)
// ---------------------------------------------------------------------------

function retrieveTopK(
  index: RetrievalIndex,
  queryEmbedding: number[] | null,
  query: string,
  k: number
): { doc: IndexDocument; score: number }[] {
  const scored = index.documents.map((doc) => {
    let score: number;
    if (queryEmbedding && doc.embedding.length === queryEmbedding.length) {
      score = cosineSimilarity(queryEmbedding, doc.embedding);
    } else {
      // Dimension mismatch or no embedding — use keyword overlap scoring
      score = keywordSimilarity(query, doc.document);
    }
    return { doc, score };
  });

  return scored.sort((a, b) => b.score - a.score).slice(0, k);
}

// ---------------------------------------------------------------------------
// RAG prompt builder (adapted from rag-query/route.ts)
// ---------------------------------------------------------------------------

function buildRagPrompt(chunks: { doc: IndexDocument; score: number }[]): string {
  const tableSchemas: Record<string, { schema: Record<string, string>; rowCount: number; notes: string }> = {};
  const categoryBlocks: string[] = [];

  for (const { doc } of chunks) {
    const meta = doc.metadata;
    const chunkType = String(meta.chunk_type ?? '');

    if (chunkType === 'schema_fields') {
      const schema = JSON.parse(String(meta.schema_json ?? '{}')) as Record<string, string>;
      const table = String(meta.table_name ?? meta.dataset_id ?? 'unknown');
      const rowCount = Number(meta.row_count ?? 0);
      const notes = String(meta.duckdb_notes ?? '');
      tableSchemas[table] = { schema, rowCount, notes };
    } else if (chunkType === 'category_vocabulary') {
      const categories = JSON.parse(String(meta.categories_json ?? '[]')) as string[];
      const table = String(meta.table_name ?? meta.dataset_id ?? 'unknown');
      if (categories.length) {
        categoryBlocks.push(`Valid categories for ${table}: ${categories.join(', ')}`);
      }
    }
  }

  let schemaSection = '';
  for (const [table, info] of Object.entries(tableSchemas)) {
    schemaSection += `\nTable '${table}' (${info.rowCount.toLocaleString()} rows):\n`;
    for (const [col, desc] of Object.entries(info.schema)) {
      schemaSection += `  ${col.padEnd(12)} -- ${desc}\n`;
    }
    if (info.notes) schemaSection += `DuckDB notes: ${info.notes}\n`;
  }

  const categorySection = categoryBlocks.length
    ? categoryBlocks.join('\n')
    : '(no category constraints — use name-based filtering if needed)';

  return `You are a SQL query generator for a DuckDB geospatial database.

## Retrieved Schema (semantic match for this query)
${schemaSection || '(no schema matched — use your best judgment)'}

## Category constraints
${categorySection}

## Output rules
- Return ONLY a valid DuckDB SQL SELECT statement. No markdown, no explanation.
- Always include: LOAD spatial; as the first line.
- SELECT id, name, category, lat, lon at minimum.
- LIMIT 200 rows unless the user specifies otherwise.
- Use ST_DWithin for proximity queries (0.005 degrees ≈ 500m at SF latitude).
- Never generate INSERT, UPDATE, DELETE, DROP, or CREATE.
- If no matching category exists, use LIKE '%keyword%' on the name column.`;
}

// ---------------------------------------------------------------------------
// LLM caller (Claude only for MCP server — no OPENAI_API_KEY dependency)
// ---------------------------------------------------------------------------

async function generateSql(systemPrompt: string, userQuery: string): Promise<string> {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    throw new Error(
      'ANTHROPIC_API_KEY not set.\n' +
      'Add it to .env.local at the project root, then restart the server.'
    );
  }
  const client = new Anthropic({ apiKey });
  const message = await client.messages.create({
    model: 'claude-sonnet-4-6',
    max_tokens: 512,
    system: systemPrompt,
    messages: [{ role: 'user', content: userQuery }],
  });
  return message.content[0].type === 'text' ? message.content[0].text.trim() : '';
}

// ---------------------------------------------------------------------------
// MCP Server
// ---------------------------------------------------------------------------

const server = new McpServer({
  name: 'scout-geo',
  version: '1.0.0',
});

// ------------------------------------------------------------------
// Tool 1: list_datasets
// Answers "what data do you have?" — the discovery meta-tool.
// Key educational point: this is why MCP beats hardcoded tool lists.
// A new client can call list_datasets to learn what exists before querying.
// ------------------------------------------------------------------

server.registerTool(
  'list_datasets',
  {
    description:
      'List all geospatial datasets available in the Scout index. ' +
      'Call this first to discover what data is available before running queries. ' +
      'Returns dataset IDs, descriptions, row counts, and spatial extents.',
  },
  async () => {
    const index = loadRetrievalIndex();
    const byDataset: Record<string, { description: string; bbox: string; rowCount: number }> = {};

    for (const doc of index.documents) {
      const meta = doc.metadata;
      const datasetId = String(meta.dataset_id ?? '?');
      const chunkType = String(meta.chunk_type ?? '');

      if (chunkType === 'title_description' && !byDataset[datasetId]) {
        const xmin = Number(meta.bbox_xmin ?? 0).toFixed(4);
        const xmax = Number(meta.bbox_xmax ?? 0).toFixed(4);
        const ymin = Number(meta.bbox_ymin ?? 0).toFixed(4);
        const ymax = Number(meta.bbox_ymax ?? 0).toFixed(4);
        const rowCount = Number(meta.row_count ?? 0);

        byDataset[datasetId] = {
          description: doc.document.slice(0, 200),
          bbox: `[${xmin}, ${ymin}, ${xmax}, ${ymax}]`,
          rowCount,
        };
      }
    }

    const datasets = Object.entries(byDataset).map(([id, info]) => ({
      dataset_id: id,
      row_count: info.rowCount,
      bbox_wgs84: info.bbox,
      description: info.description,
    }));

    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify({ datasets, index_model: index.model, exported_at: index.exported_at }, null, 2),
      }],
    };
  }
);

// ------------------------------------------------------------------
// Tool 2: explain_schema
// Returns column names and descriptions for a specific dataset.
// Key educational point: LLM clients use this to understand what SQL
// columns are valid before writing a query — self-correcting behavior.
// ------------------------------------------------------------------

server.registerTool(
  'explain_schema',
  {
    description:
      'Get the full column schema and DuckDB notes for a specific dataset. ' +
      'Use the dataset_id values returned by list_datasets. ' +
      'Call this before writing SQL to ensure you use valid column names.',
    inputSchema: {
      dataset_id: z.string().describe(
        'The dataset identifier, e.g. "sf-places-2026" or "sf-buildings-2026"'
      ),
    },
  },
  async ({ dataset_id }) => {
    const index = loadRetrievalIndex();
    const schemaDoc = index.documents.find(
      (d) =>
        String(d.metadata.dataset_id) === dataset_id &&
        String(d.metadata.chunk_type) === 'schema_fields'
    );

    if (!schemaDoc) {
      return {
        content: [{
          type: 'text' as const,
          text: JSON.stringify({
            error: `No schema found for dataset_id="${dataset_id}"`,
            available_dataset_ids: [...new Set(index.documents.map((d) => String(d.metadata.dataset_id)))],
          }, null, 2),
        }],
        isError: true,
      };
    }

    const meta = schemaDoc.metadata;
    const schema = JSON.parse(String(meta.schema_json ?? '{}')) as Record<string, string>;
    const tableName = String(meta.table_name ?? dataset_id);
    const rowCount = Number(meta.row_count ?? 0);
    const notes = String(meta.duckdb_notes ?? '');

    // Format schema as a readable table
    const schemaLines = Object.entries(schema)
      .map(([col, desc]) => `  ${col.padEnd(14)} — ${desc}`)
      .join('\n');

    const text = [
      `Dataset: ${dataset_id}`,
      `Table name in SQL: '${tableName}'`,
      `Row count: ${rowCount.toLocaleString()}`,
      '',
      'Columns:',
      schemaLines,
      ...(notes ? ['', 'DuckDB notes:', `  ${notes}`] : []),
    ].join('\n');

    return {
      content: [{ type: 'text' as const, text }],
    };
  }
);

// ------------------------------------------------------------------
// Tool 3: query_places
// NL → SQL via the RAG pipeline (same as /api/scout/rag-query).
// Key educational point: this is the composability payoff — the Vector RAG
// pipeline runs unchanged inside a completely different interface.
// ------------------------------------------------------------------

server.registerTool(
  'query_places',
  {
    description:
      'Translate a natural language question about places in San Francisco into ' +
      'a DuckDB SQL SELECT statement. Uses vector search to retrieve relevant ' +
      'schema context before generating SQL. ' +
      'Returns SQL that can be executed against the Scout GeoParquet files. ' +
      'Example: "Show me coffee shops near Dolores Park"',
    inputSchema: {
      nl_query: z.string().describe(
        'Natural language question about places in San Francisco, e.g. "Find all hospitals" or "Restaurants within 500m of Union Square"'
      ),
    },
  },
  async ({ nl_query }) => {
    const index = loadRetrievalIndex();

    // Step 1: retrieve relevant schema chunks (keyword fallback — no embedding API needed)
    const topK = retrieveTopK(index, null, nl_query, TOP_K);
    const used = topK.filter((item) => item.score >= SIM_THRESHOLD);

    // Always include at least the sf-places schema_fields chunk so the LLM
    // knows the column names, even if no chunks clear the threshold.
    if (used.length === 0) {
      const fallbackChunk = index.documents.find(
        (d) =>
          String(d.metadata.dataset_id) === 'sf-places-2026' &&
          String(d.metadata.chunk_type) === 'schema_fields'
      );
      if (fallbackChunk) used.push({ doc: fallbackChunk, score: 0 });
    }

    // Step 2: build a targeted RAG system prompt
    const systemPrompt = buildRagPrompt(used);

    // Step 3: call Claude to generate SQL
    const sql = await generateSql(systemPrompt, nl_query);

    const chunksUsed = used.map((item) => ({
      id: item.doc.id,
      similarity: Math.round(item.score * 1000) / 1000,
      chunk_type: String(item.doc.metadata.chunk_type ?? ''),
    }));

    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify({ sql, chunks_used: chunksUsed, top_k_fetched: TOP_K }, null, 2),
      }],
    };
  }
);

// ------------------------------------------------------------------
// Tool 4: get_map_extent
// Returns the current SF map viewport bbox.
// Key educational point: in a real integration, this would read from
// the live MapLibre map via a browser bridge. For the standalone MCP
// server, we return a hardcoded SF bbox.
// ------------------------------------------------------------------

server.registerTool(
  'get_map_extent',
  {
    description:
      'Returns the current map viewport bounding box as {west, south, east, north} in WGS84 degrees. ' +
      'Use this to scope queries to the area the user is currently viewing. ' +
      'In the Scout web app, this reads the live MapLibre viewport. ' +
      'In the standalone MCP server, returns the default San Francisco bounding box.',
  },
  async () => {
    const bbox = {
      west: -122.5152,
      south: 37.7079,
      east: -122.3591,
      north: 37.8324,
      _note: 'Default SF bounding box. In the Scout web UI, this reads the live MapLibre viewport via map.getBounds().',
    };
    return {
      content: [{ type: 'text' as const, text: JSON.stringify(bbox, null, 2) }],
    };
  }
);

// ---------------------------------------------------------------------------
// Start server
// ---------------------------------------------------------------------------

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  // MCP servers communicate via stdio — do not write to stdout after connect.
  // Use stderr for debug logging so it doesn't corrupt the JSON-RPC stream.
  process.stderr.write('[scout-geo] MCP server started. Listening on stdio.\n');
}

main().catch((err) => {
  process.stderr.write(`[scout-geo] Fatal error: ${err}\n`);
  process.exit(1);
});
