/**
 * Scout Module 31 — Generative Query API Route
 * ================================================
 * POST /api/scout/generative-query
 *
 * Extends the agent-query pattern (Module 27) with structured visualization output.
 * The LLM uses two tools:
 *   - execute_sql:          explores available data (same as agent-query)
 *   - return_visualization: terminal action — returns SQL + LayerConfig + viewport
 *
 * This is "generative UI": the LLM decides not just what data to show, but HOW
 * to show it. Color, radius, and layer type are chosen based on query semantics.
 *
 * Request body:
 *   {
 *     query: string,
 *     bbox?: { west, south, east, north }
 *   }
 *
 * Response:
 *   {
 *     sql: string,
 *     layer_config: LayerConfig,
 *     viewport?: { longitude, latitude, zoom },
 *     reasoning: string,
 *     reasoning_trace: ToolCall[],
 *     provider: string,
 *   }
 */

import { NextRequest, NextResponse } from 'next/server';
import Anthropic from '@anthropic-ai/sdk';
import { buildDatasetSystemPromptSection } from '@/lib/scout-datasets-server';
import { validateSql, enforceLimitClause } from '@/lib/scout-guards';
import { checkRateLimit } from '@/lib/rate-limit';
import { getLlmAccess } from '@/lib/llm-access';
import { DEFAULT_LAYER_CONFIG } from '@/lib/scout-layer-config';
import type { LayerConfig, ToolCall } from '@/lib/scout-types';
import { PIPELINE } from '@/lib/scout-pipeline';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface BoundingBox {
  west: number;
  south: number;
  east: number;
  north: number;
}

interface Viewport {
  longitude: number;
  latitude: number;
  zoom: number;
}

interface GenerativeResult {
  sql: string;
  layer_config: LayerConfig;
  viewport?: Viewport;
  reasoning: string;
  reasoning_trace: ToolCall[];
  provider: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MAX_AGENT_TURNS = 8;

// ---------------------------------------------------------------------------
// Tool definitions
// ---------------------------------------------------------------------------

const TOOLS: Anthropic.Tool[] = [
  {
    name: 'execute_sql',
    description:
      'Execute a DuckDB SQL SELECT against the Scout geospatial database to explore data. ' +
      'Start every query with "LOAD spatial;". ' +
      'Returns {row_count, columns, sample_rows} on success, or {error} on failure. ' +
      'Use this to understand the data before calling return_visualization.',
    input_schema: {
      type: 'object' as const,
      properties: {
        sql: {
          type: 'string',
          description: 'Complete DuckDB SQL SELECT. First line must be "LOAD spatial;"',
        },
      },
      required: ['sql'],
    },
  },
  {
    name: 'return_visualization',
    description:
      'Signal that you have finished and return the final SQL + visualization config. ' +
      'Call this once you know the correct SQL and have chosen an appropriate visual style.',
    input_schema: {
      type: 'object' as const,
      properties: {
        sql: { type: 'string', description: 'The final DuckDB SQL SELECT to execute in the browser' },
        layer_config: {
          type: 'object' as const,
          properties: {
            type: { type: 'string', enum: ['circle', 'heatmap'] },
            color: {
              type: 'array',
              items: { type: 'number' },
              minItems: 3,
              maxItems: 3,
              description: 'RGB color array [R, G, B] each 0-255',
            },
            radius: { type: 'number', minimum: 3, maximum: 20 },
            opacity: { type: 'number', minimum: 0, maximum: 1 },
            label: { type: 'string', description: 'Human-readable style description' },
          },
          required: ['type', 'color', 'radius', 'opacity'],
        },
        viewport: {
          type: 'object' as const,
          properties: {
            longitude: { type: 'number' },
            latitude: { type: 'number' },
            zoom: { type: 'number' },
          },
          description: 'Optional viewport hint to fly the map to',
        },
        reasoning: {
          type: 'string',
          description: 'Explain your color/style choices in plain English',
        },
      },
      required: ['sql', 'layer_config', 'reasoning'],
    },
  },
];


// ---------------------------------------------------------------------------
// LayerConfig validation — clamp values rather than reject
// ---------------------------------------------------------------------------

function validateAndNormalizeLayerConfig(raw: unknown): LayerConfig {
  if (!raw || typeof raw !== 'object') return { ...DEFAULT_LAYER_CONFIG };

  const obj = raw as Record<string, unknown>;

  const type: 'circle' | 'heatmap' =
    obj.type === 'circle' || obj.type === 'heatmap' ? obj.type : DEFAULT_LAYER_CONFIG.type;

  // Validate color array: must be 3 numbers each 0-255
  let color: [number, number, number] = [...DEFAULT_LAYER_CONFIG.color];
  if (Array.isArray(obj.color) && obj.color.length >= 3) {
    const [r, g, b] = obj.color as unknown[];
    const clamp = (v: unknown) => Math.max(0, Math.min(255, Math.round(Number(v) || 0)));
    color = [clamp(r), clamp(g), clamp(b)];
  }

  const clampNum = (v: unknown, min: number, max: number, fallback: number): number => {
    const n = Number(v);
    return isNaN(n) ? fallback : Math.max(min, Math.min(max, n));
  };

  const radius = clampNum(obj.radius, 3, 20, DEFAULT_LAYER_CONFIG.radius);
  const opacity = clampNum(obj.opacity, 0, 1, DEFAULT_LAYER_CONFIG.opacity);
  const label = typeof obj.label === 'string' ? obj.label : undefined;

  return { type, color, radius, opacity, ...(label ? { label } : {}) };
}

// ---------------------------------------------------------------------------
// System prompt
// ---------------------------------------------------------------------------

function buildSystemPrompt(): string {
  return `You are a geospatial visualization assistant. Given a natural language query about San Francisco places:
1. Use execute_sql to find the right SQL query using the available datasets.
2. Then call return_visualization with:
   - The final SQL query
   - A layer_config that matches the semantic intent of the query:
     * color: choose an intuitive RGB color (e.g., green for parks, orange for restaurants, blue for water)
     * type: 'circle' for point data, 'heatmap' for density queries
     * radius: 6-12 depending on expected result density
     * opacity: 0.7-0.9
   - A reasoning string explaining your color/style choices

${buildDatasetSystemPromptSection()}

## CRITICAL DuckDB spatial rules
1. **NEVER use ST_GeomFromWKB()** — geometry columns are already native GEOMETRY type.
2. For proximity queries use Haversine approximation or degrees distance:
   \`\`\`sql
   LOAD spatial;
   SELECT id, name, category, lat, lon
   FROM places
   WHERE category IN ('coffee_shop')
     AND ABS(lat - 37.7596) < 0.01 AND ABS(lon - (-122.4269)) < 0.01
   LIMIT 200;
   \`\`\`
3. Do NOT use SELECT *, never include geometry columns in SELECT
4. Always start with: LOAD spatial;
5. LIMIT 200 rows unless otherwise asked
6. Never use INSERT, UPDATE, DELETE, DROP, CREATE`;
}

// ---------------------------------------------------------------------------
// Agent loop
// ---------------------------------------------------------------------------

async function runGenerativeLoop(
  query: string,
  bbox: BoundingBox | undefined // eslint-disable-line @typescript-eslint/no-unused-vars
): Promise<GenerativeResult> {
  const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

  const messages: Anthropic.MessageParam[] = [{ role: 'user', content: query }];

  const trace: ToolCall[] = [];
  let finalSql: string | null = null;
  let layerConfig: LayerConfig = { ...DEFAULT_LAYER_CONFIG };
  let viewport: Viewport | undefined;
  let reasoning = '';

  for (let turn = 0; turn < MAX_AGENT_TURNS; turn++) {
    const response = await client.messages.create({
      model: PIPELINE.CLAUDE_MODEL,
      max_tokens: PIPELINE.MAX_TOKENS * 4,
      system: buildSystemPrompt(),
      tools: TOOLS,
      messages,
    });

    if (response.stop_reason === 'end_turn') break;
    if (response.stop_reason !== 'tool_use') break;

    messages.push({ role: 'assistant', content: response.content });

    const toolResults: Anthropic.ToolResultBlockParam[] = [];

    for (const block of response.content) {
      if (block.type !== 'tool_use') continue;

      const stepStart = Date.now();
      const input = block.input as Record<string, unknown>;
      let output: string;

      if (block.name === 'return_visualization') {
        // Terminal action — extract and validate, then stop the loop
        const rawSql = input.sql as string;
        const validation = validateSql(rawSql);

        if (validation.valid) {
          finalSql = enforceLimitClause(rawSql);
        } else {
          // SQL is invalid — fall back, but still return what we have
          output = JSON.stringify({ error: `SQL rejected: ${validation.reason}` });
          trace.push({
            step: trace.length + 1,
            tool: block.name,
            input,
            output: output.slice(0, 300),
            elapsed_ms: Date.now() - stepStart,
          });
          break;
        }

        layerConfig = validateAndNormalizeLayerConfig(input.layer_config);
        reasoning = typeof input.reasoning === 'string' ? input.reasoning : '';

        if (input.viewport && typeof input.viewport === 'object') {
          const vp = input.viewport as Record<string, unknown>;
          viewport = {
            longitude: Number(vp.longitude) || -122.43,
            latitude: Number(vp.latitude) || 37.77,
            zoom: Number(vp.zoom) || 12,
          };
        }

        trace.push({
          step: trace.length + 1,
          tool: block.name,
          input,
          output: JSON.stringify({ sql: finalSql, layer_config: layerConfig }).slice(0, 300),
          elapsed_ms: Date.now() - stepStart,
        });

        // return_visualization is terminal — exit the loop immediately
        return {
          sql: finalSql ?? '',
          layer_config: layerConfig,
          viewport,
          reasoning,
          reasoning_trace: trace,
          provider: `claude-generative (${PIPELINE.CLAUDE_MODEL})`,
        };
      }

      if (block.name === 'execute_sql') {
        // Server-side: we can't run DuckDB-Wasm. Return a mock success so the
        // loop can continue and the agent will call return_visualization next.
        // The actual SQL execution happens in the browser via LabMap.
        const sql = input.sql as string;
        const validation = validateSql(sql);

        if (!validation.valid) {
          output = JSON.stringify({ error: `SQL rejected: ${validation.reason}` });
        } else {
          // Return a realistic-looking mock so the agent has something to reason about
          output = JSON.stringify({
            note: 'SQL will be executed in the browser (DuckDB-Wasm). Assume it works. Call return_visualization with this SQL.',
            sql_preview: sql.slice(0, 200),
          });
          // Stash as candidate SQL in case agent never calls return_visualization
          finalSql = enforceLimitClause(sql);
        }

        trace.push({
          step: trace.length + 1,
          tool: block.name,
          input,
          output: output.slice(0, 300),
          elapsed_ms: Date.now() - stepStart,
        });

        toolResults.push({ type: 'tool_result', tool_use_id: block.id, content: output });
        continue;
      }

      output = JSON.stringify({ error: `Unknown tool: ${block.name}` });
      trace.push({
        step: trace.length + 1,
        tool: block.name,
        input,
        output: output.slice(0, 300),
        elapsed_ms: Date.now() - stepStart,
      });
      toolResults.push({ type: 'tool_result', tool_use_id: block.id, content: output });
    }

    if (toolResults.length > 0) {
      messages.push({ role: 'user', content: toolResults });
    }
  }

  // Fell through the loop without return_visualization being called —
  // return whatever SQL we accumulated with the default layer config.
  return {
    sql: finalSql ?? '',
    layer_config: layerConfig,
    viewport,
    reasoning: reasoning || 'Agent completed without explicit visualization reasoning.',
    reasoning_trace: trace,
    provider: `claude-generative (${PIPELINE.CLAUDE_MODEL})`,
  };
}

// ---------------------------------------------------------------------------
// POST handler
// ---------------------------------------------------------------------------

export async function POST(request: NextRequest) {
  const ip = request.headers.get('x-forwarded-for') ?? '127.0.0.1';
  if (!checkRateLimit(ip)) {
    return NextResponse.json(
      { error: 'Too many requests. Please try again later.' },
      { status: 429 }
    );
  }

  // LLM spend gate: must run before any API key is read or client constructed.
  const llmAccess = await getLlmAccess();
  if (llmAccess.mode !== 'live') {
    return NextResponse.json({ error: 'live_llm_disabled', mode: 'replay' }, { status: 403 });
  }

  let query: string;
  let bbox: BoundingBox | undefined;

  try {
    const body = await request.json();
    query = body?.query?.trim();
    bbox = body?.bbox;

    if (!query) {
      return NextResponse.json({ error: 'Missing required field: query' }, { status: 400 });
    }
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  if (!process.env.ANTHROPIC_API_KEY) {
    return NextResponse.json(
      { error: 'Missing API key', details: 'Set ANTHROPIC_API_KEY in your .env.local file.' },
      { status: 503 }
    );
  }

  try {
    const result = await runGenerativeLoop(query, bbox);

    return NextResponse.json({
      sql: result.sql,
      layer_config: result.layer_config,
      viewport: result.viewport,
      reasoning: result.reasoning,
      reasoning_trace: result.reasoning_trace,
      provider: result.provider,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      { error: 'Generative query loop failed', details: message },
      { status: 502 }
    );
  }
}
