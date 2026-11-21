> Status: Elective / Extended Module — complete the Scout Phase modules first.

## Overview

Agentic geospatial queries let an LLM autonomously decide which spatial tools to call, chain multiple operations together, and return map-ready results — without the user specifying the exact steps. Where Scout Phase 2 is a single-turn translation (question → SQL), an agent takes multi-step reasoning: searching for relevant datasets, executing intermediate queries, reading results, and deciding what to do next. The module covers tool-use patterns, the agent loop, and how compound error rates affect reliability.

## Key Concepts

### 1. Tool-Use / Function-Calling Pattern

Modern LLMs support structured function calling: instead of returning free text, the model returns a JSON object specifying which function to call and with what arguments. The application executes the function and feeds the result back to the model. For geospatial agents, the tools are operations like `search_datasets`, `execute_sql`, `get_map_extent`, and `ask_clarification` — each backed by a real implementation the agent can call mid-conversation.

### 2. The Agent Loop: Plan → Call → Observe → Repeat

An agent does not complete its task in a single LLM call. It plans a step, calls a tool, observes the result, and decides what to do next — repeating until it reaches a final answer or a maximum step count. This loop enables multi-step site selection (find coffee-dense H3 cells, subtract park cells, return the difference), self-correcting SQL (catch a column error, look up the schema, retry), and progressive refinement. Each round-trip adds latency, so the loop length is a product trade-off.

### 3. Reliability Compounds with Step Count

A non-agentic system with 90% reliability succeeds 90% of the time. A 5-step agent where each step has 90% reliability succeeds roughly 59% of the time. This compounding failure rate is why production agent systems invest heavily in tool guardrails, fallbacks, and observability. Every tool call and its result must be logged to support debugging — this is a product requirement, not a nice-to-have.

## 1. What Changes with Agents

In a non-agentic system, the conversation is linear: user sends a question,
the system builds a prompt, the LLM returns SQL, the system renders the map.
In an agentic system, a single user question like "Find areas with high coffee
density but no parks" triggers a multi-step reasoning loop: the agent searches
for the coffee dataset, executes a density aggregation query, searches for the
parks dataset, executes a park coverage query, computes the set difference, and
returns a final result with its reasoning.

The user asked one question. The agent took five steps. This is only possible
because the LLM can call functions (tools) mid-conversation and use the results
to decide what to do next.

## 2. LLM Tool Calling

Modern LLMs support structured function calling. Instead of returning free text,
the model returns a structured JSON object specifying which function to call and
with what arguments. The application executes the function and feeds the result
back to the model.

Both Anthropic and OpenAI support this pattern — Anthropic calls it "tool use"
and OpenAI calls it "function calling." They use slightly different syntax but
converged on a similar API design. The tool definition includes a name,
description, and an input schema that tells the model exactly what arguments to
provide.

For Scout, the relevant tools are `search_datasets` (find relevant schemas by
semantic similarity), `execute_sql` (run a DuckDB query against GeoParquet
files), `get_map_extent` (read the current viewport bounds), and
`ask_clarification` (request more information when the query is genuinely
ambiguous).

**OpenAI function calling** uses the same concept with slightly different syntax
(`functions` → `tools`, `function_call` → `tool_calls`). Both providers
converged on a similar API in 2024.

## 3. Why This Matters for Product Patterns

Agents represent the frontier of LLM product architecture. Understanding where
they add value (and where they add fragility) is a critical PM skill:

- **When agents win**: Multi-step reasoning, exploratory queries ("what's
  interesting in this dataset?"), debugging ("why did the last query return
  nothing?"), and tasks where the user can't fully specify the intent upfront.
- **When agents lose**: Latency-sensitive applications (each tool call adds a
  round-trip), cost-sensitive applications (5 LLM calls instead of 1),
  high-stakes decisions requiring human oversight at each step, and cases where
  the tools are unreliable (garbage in → garbage out amplified by 5x).
- **The reliability challenge**: An agent's error rate compounds. If each step
  has 90% reliability, a 5-step agent succeeds 59% of the time. This is why
  production agent systems invest heavily in tool guardrails, fallbacks, and
  human-in-the-loop checkpoints.
- **Observability becomes critical**: When a non-agentic query fails, you see
  one LLM call. When an agent fails, you need to trace which tool call, with
  what arguments, produced the bad intermediate result. This is a product
  requirement: "The system must log every tool call and its result for
  debugging."

## 5. Geospatial-Specific Agent Patterns

### Self-Correcting SQL

If `execute_sql` returns an error (invalid column name, wrong function
signature), the agent can read the error, look up the correct schema with
`get_schema`, and retry. This is genuinely useful because LLMs make SQL mistakes
even with good prompts, and a one-shot system exposes those errors to the user.
An agent can silently fix them.

### Progressive Spatial Refinement

The multi-step site selection pattern mirrors what GIS analysts do manually:
get the map extent, aggregate coffee shop density by H3 cell, aggregate foot
traffic by H3 cell, calculate the ratio, and summarize the reasoning. The agent
is doing spatial analysis, not just answering a lookup question.

### Uncertainty Handling

An agent can call `ask_clarification` when the query is genuinely ambiguous
instead of making an assumption silently. "Did you mean coffee shops in the
Financial District, or across all of SF?" is a better user experience than a
query with wrong spatial scope.

---

## 6. Exercises (Planned)

### Exercise 1: Build the Tool Definitions

Define the tool schemas for `search_datasets`, `execute_sql`, and
`get_map_extent`. Implement the handler functions that back each tool.

### Exercise 2: Single-Step Agent Baseline

Replace the current `POST /api/scout/query` route with an agent that uses
`search_datasets` to retrieve schema context before generating SQL. Verify it
produces equivalent output to Phase 2's direct approach.

### Exercise 3: Multi-Step Agent

Enable the agent to call `execute_sql`, read the results, and optionally call it
again with a refined query. Test with questions that require multiple SQL
statements to answer.

### Exercise 4: Observability Layer

Add logging middleware that records every tool call, its input, its output, and
the elapsed time. Display the "reasoning trace" in the Scout UI below the
results.

The exercise files live at `src/exercises/agentic/`: `01_tool_definitions.ts`,
`02_single_step_agent.md`, `03_multi_step_agent.ts`, and `04_observability.ts`.

### What to Observe

- **Latency vs. capability trade-off**: Time a single-step query (Phase 2
  approach) vs. a multi-step agent query. The agent takes longer — is the output
  quality improvement worth it for your use case?
- **Error recovery**: Deliberately give the agent a query that will produce
  invalid SQL on first try. Watch it catch the error and retry. This is
  genuinely impressive and genuinely fragile at the same time.
- **Cost accounting**: Log token usage across all steps of a multi-step query.
  Multiply by your provider's per-token price. This is your per-query cost for
  the agentic version. Compare to Phase 2's single-call cost.
- **The reasoning trace**: Read the intermediate tool calls the agent made. Do
  they match how a human GIS analyst would approach the same problem? Where does
  the agent take a shortcut that a human wouldn't?

---

## 7. The Bigger Picture: AI-Native GIS

The Scout elective modules trace a progression that mirrors what's happening across
the GIS industry right now:

| Approach             | Product example                      | Limitation                      |
| -------------------- | ------------------------------------ | ------------------------------- |
| Prompt stuffing      | Scout                                | Single dataset, fixed schema    |
| RAG over schemas     | Databricks Genie, Snowflake Copilot  | Retrieval quality ceiling       |
| Agents with tools    | Emerging — Esri R&D, Felt AI roadmap | Latency, cost, reliability      |
| Spatial-aware agents | Research frontier                    | No widely-deployed products yet |

The spatial-aware agent — one that understands that "near", "within", and
"adjacent to" are different from "similar to" — is the unsolved problem at the
frontier. If you're working in geospatial product, this is the space where the
interesting product bets are being made.

## Practical Exercises


