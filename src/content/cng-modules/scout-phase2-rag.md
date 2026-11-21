> **Live App & Exercise Access**: Interactive tools in this track (such as the
> live **Scout** interface or spatial evaluation tools) are **not yet public**.
> If you would like to test these applications, please **reach out to the
> author**.

## Overview

Phase 2 implements the translation layer that converts a user's natural language question into executable DuckDB SQL. Rather than true RAG with a vector database, Scout uses context injection — the STAC catalog built in Phase 1 is small enough to fit entirely in a single prompt, so it is injected directly at request time. The result is a typed Next.js API route that accepts a plain-English query and returns a SQL statement ready for DuckDB-Wasm to execute in the browser.

## Key Concepts

### 1. Context Injection vs. RAG

Scout's "knowledge base" is already small and perfectly structured: the STAC catalog JSON from Phase 1. Because it fits in the model's context window and is already machine-readable, injecting it directly into the system prompt is simpler, faster, and more auditable than building a vector database. This pattern — sometimes called "prompt stuffing" — is the right architectural choice when your reference data is small and stable.

### 2. Prompt Engineering as Product Work

The system prompt that constrains the LLM is a product artifact: it encodes business rules (only return results within the SF bounding box), data quality standards (use `ST_DWithin` instead of rectangular approximations), and safety constraints (never generate `DELETE` or `DROP` statements). It should be version-controlled and reviewed like code, because every line of generated SQL reflects a decision embedded in the prompt.

### 3. The LLM as a Closed-Vocabulary Translator

The LLM is not reasoning about geography — it is doing precise string substitution into a known template space. By injecting the STAC catalog's category vocabulary into the system prompt, the model is constrained to use only valid category values (e.g., `coffee_shop`, not `cafe` or `coffee-shop`). This vocabulary injection is the single biggest reliability win of the prompt-stuffing approach.

## 1. The Problem: Natural Language to SQL

SQL is precise. Natural language is not. The user says "near" — the database
needs `ST_DWithin`. The user says "coffee shop" — the database needs
`category = 'coffee_shop'` (with an underscore, not a space, and matching the
exact string that Overture uses). The user says "big park" — that's undefined;
we need to pick a sensible interpretation.

A **Language Model** is well-suited for this translation problem, but only if it
has the right context. A model asked to write SQL for an unknown table will
hallucinate column names, make up category values, and produce queries that fail
silently. We need to constrain it.

## 2. RAG vs. Prompt-with-Context

The stub for this module mentioned **RAG (Retrieval-Augmented Generation)** —
the pattern where you embed a large knowledge base, find the most relevant
chunks with vector search, and inject them into the prompt.

For Scout, that's more complexity than we need. Our "knowledge base" is already
small and perfectly structured: it's the STAC catalog we built in Phase 1. The catalog
JSON is a few kilobytes — it fits entirely in a single prompt.

This pattern is sometimes called **"prompt stuffing"** or **"context
injection"**, and it's the right architectural choice when:

- The reference data fits in the model's context window (ours does)
- The reference data is already structured (STAC JSON is machine-readable)
- You don't need semantic similarity ranking across millions of documents

We read the STAC catalog at request time and inject the relevant fields directly
into the system prompt. Simple, fast, cheap, and auditable.

## 3. Why This Matters for Product Patterns

This module is where the biggest architectural bets get made:

- **LLM provider is a business risk**: Locking into a single provider couples
  your reliability and pricing to one vendor. A `LLM_PROVIDER` environment
  variable that switches between Anthropic and OpenAI is not just a developer
  convenience — it's a negotiating chip and a hedging strategy. Model your
  contract accordingly.
- **Prompt engineering is product work**: The system prompt that constrains the
  LLM's output is a product artifact as much as a technical one. It encodes
  business rules ("only return results within the SF bounding box"), data
  quality standards ("always use ST_DWithin instead of approximations"), and
  user safety constraints ("never generate DELETE or DROP statements"). It
  should be version-controlled and reviewed like code.
- **Error handling is a UX surface**: When the LLM returns invalid SQL, the user
  sees a failure. How that failure is communicated, logged, and retried is a
  product decision. Graceful degradation (e.g., "I couldn't understand that
  query — try rephrasing?") is significantly better than a 500 error.
- **Cost per query is a unit economics input**: LLM API calls cost money. The
  size of your system prompt, the model tier you choose, and the frequency of
  requests all feed directly into your cost model. A PM who can read a token
  usage dashboard and connect it to feature decisions is valuable.

## 4. The System Prompt: Giving the LLM Constraints

The quality of the SQL output depends almost entirely on the quality of the
system prompt. A well-engineered prompt does three things:

**Define the schema precisely** — telling the LLM exactly which table and columns exist, their types, and their purpose. Without this, the model invents column names.

**Provide the closed vocabulary** — injecting the full list of valid category values from the STAC catalog's `scout:categories` field, instructing the model to use them exactly as written. This is the key reliability mechanism.

**State output constraints** — rules like "return only a valid DuckDB `SELECT` statement with no explanation," "always load the spatial extension," "use `ST_DWithin` for proximity queries," and "never generate `INSERT`, `UPDATE`, `DELETE`, `DROP`, or `CREATE` statements."

This combination of schema + vocabulary + rules produces reliable, executable
SQL. The LLM is not reasoning about geography — it's doing precise string
substitution into a known template space.

### Exercise 1: Test the Prompt in Isolation

**Motivating Question**: "Before wiring anything into the app, can I verify that
the LLM actually produces correct SQL for my dataset?"

In this exercise, you will write and test the prompt as a standalone Python
script, before building the API route. This is how professional ML engineers
iterate on prompts — in isolation, with a tight feedback loop.

Make sure you have completed the Phase 1 exercises — the script reads the STAC
item directly from `src/exercises/scout-phase1-etl/output/stac/`. Add your
`ANTHROPIC_API_KEY` (or `OPENAI_API_KEY`) to `.env.local` at the project root,
then run `01_test_prompt.py` from the exercise directory. Observe the SQL output:
does it use the correct column names? Are the category values from the STAC
catalog's closed list?

**Key things to notice in the script:**

- The script reads the STAC item JSON and extracts `scout:categories` to build
  the vocabulary list dynamically. The prompt always reflects the actual data.
- Try a deliberately ambiguous query ("show me places to eat") and see how the
  model interprets it.
- Try a query with a category that doesn't exist ("show me sushi restaurants")
  and see if the model falls back to the nearest valid category or refuses.

---

## Reading the Output: Every Line Is a Product Decision

After running Exercise 1, one of the test queries produces output similar to:

`LOAD spatial; SELECT id, name, category, lat, lon FROM places WHERE category IN ('park', 'playground') AND lat BETWEEN 37.773 AND 37.788 AND lon BETWEEN -122.513 AND -122.450 ORDER BY name LIMIT 200;`

This looks correct. It probably _is_ correct. But every single line is a product
decision — some you made explicitly, some the LLM made for you silently, and
some you didn't realize you were making at all.

### Line by line

**`LOAD spatial;`** This comes from the system prompt rule: "Always include LOAD
spatial; as the first statement." It's necessary when ST_* functions are used.
This query doesn't actually use any spatial functions (it's a bbox via BETWEEN,
not ST_DWithin), so the instruction is followed but irrelevant here. The LLM
obeyed the rule without checking whether it applied. Minor, harmless — but this
is how prompt rules interact with specific queries in practice.

**`category IN ('park', 'playground')`** This is the closed-vocabulary
constraint working exactly as designed. "Parks and playgrounds" mapped cleanly
to two values from the `scout:categories` list in the STAC item. The LLM did not
invent `green_space` or `recreation_area` because those aren't in the
vocabulary. This is the biggest reliability win of the prompt-stuffing approach.

**`lat BETWEEN 37.773 AND 37.788 AND lon BETWEEN -122.513 AND -122.450`** This
is where things get interesting — and where a PM needs to ask hard questions.

The user said "in the Richmond." The LLM produced a bounding box. Where did
those coordinates come from? **Not from our data. Not from our prompt. From the
LLM's training data.** The model has seen enough text about San Francisco
neighborhoods to know roughly where the Richmond district is, and it encoded
that knowledge as a lat/lon rectangle.

This has several implications:

1. **You cannot audit it.** There is no source of truth to check these
   coordinates against. If Claude's training data had a slightly wrong
   definition of the Richmond's boundary, you'd never know until a user
   complained that their favorite park wasn't in the results.

2. **It is not version-controlled.** When you upgrade from one model version
   to the next, the coordinates for "the Richmond" might silently shift.
   Your test suite for the prompt wouldn't catch it unless you specifically
   tested that the returned rows are geographically correct.

3. **It only works for places the LLM knows.** "Show me coffee shops in the
   Tenderloin" will work. "Show me coffee shops in the Dogpatch" might work.
   "Show me coffee shops near the intersection of 19th and Noriega" might not.
   The LLM's geographic knowledge is uneven and not documented.

4. **The bbox is rectangular, not the actual neighborhood boundary.** The
   Richmond has a real boundary that's not a rectangle. Places near the corners
   of this bbox may not be in the Richmond; places near the edges of the true
   neighborhood may be excluded. For most use cases this is fine — but if
   precision matters (city planning, real estate, healthcare access), this is a
   reliability problem.

**`ORDER BY name`** The user did not ask for alphabetical ordering. **The LLM
chose it.** Why not order by proximity to the center of the Richmond? Why not by
confidence score? The model made a sorting decision that affects what the user
sees first on the map. This is a product decision you did not write a spec for.
If the answer to "what should users see first?" matters to your product, it
needs to be in the system prompt.

**`LIMIT 200`** Comes directly from the system prompt rule: "LIMIT results to
200 rows unless the user specifies otherwise." 200 is a number someone chose. If
the Richmond has 150 parks and playgrounds in the dataset, 200 is fine. If a
broader query returns 150,000 results and the frontend tries to render all of
them, the map will freeze. The limit is a UX contract — changing it is a product
decision with frontend consequences.

### The geography problem in depth: what else could we have done?

"In the Richmond" as an input is genuinely hard. Here are the real architectural
options, with their trade-offs:

| Approach                          | How it works                                                                                                                         | Accuracy                             | Complexity                                         | Risk                                                 |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------ | -------------------------------------------------- | ---------------------------------------------------- |
| **LLM training data** (current)   | Model infers bbox from what it learned                                                                                               | Medium — uneven by neighborhood fame | Zero — it just works                               | Unauditable, changes with model upgrades             |
| **Neighborhood polygon dataset**  | Load SF neighborhood boundaries as a second GeoParquet; supply the polygon in the prompt; use `ST_Within`                            | High — exact boundary                | Medium — requires second ETL, prompt grows         | Dataset must be kept current                         |
| **Geocoding API at query time**   | Add a pre-processing step that calls Nominatim or Google Maps to resolve "the Richmond" to a polygon, then inject it into the prompt | High — real-time authoritative       | High — adds latency (~200ms), API dependency, cost | Rate limits, API key management                      |
| **Structured neighborhood input** | Force the UI to have the user select a neighborhood from a dropdown before querying                                                  | Exact — no ambiguity                 | Low for backend, higher for UX                     | Users hate dropdowns; reduces the NL interface value |
| **Ask for clarification**         | LLM calls an `ask_clarification` tool when geographic input is ambiguous                                                             | N/A — deferred to user               | Low initially, but requires agentic pattern        | Adds a round-trip; increases latency                 |
| **Geographic embeddings**         | Embed neighborhood descriptions in a vector store; retrieve the closest polygon to the user's text                                   | Medium-high                          | Very high — research-grade tooling                 | No production-ready library for this yet             |

For Scout's demo scale, the current approach (LLM training data) is the right
call. But you should make this choice explicitly and document it — not discover
it by reading the SQL output six months later.

### The PM checklist for any NL-to-SQL system

After running Exercise 1, go through each line of each generated query and ask:

- **Where did this value come from?** Prompt → STAC catalog → LLM training data?
- **What would break if it were wrong?** Silent wrong results, visible error,
  crash?
- **Who would catch it?** User complaint? Automated test? Nobody?
- **What is the product spec for this behavior?** Written down anywhere?

The prompt is a product artifact. The decisions embedded in it — default
proximity radius, result limit, ordering, geographic resolution strategy — are
product specs. Treat them that way: version control them, review changes, and
write tests that exercise the edge cases.

---

### Exercise 2: Build the Next.js API Route

**Motivating Question**: "How do we expose this LLM translation as a typed,
error-handled HTTP endpoint that the frontend can call?"

This exercise implements `src/app/api/scout/query/route.ts` — the only server-
side component of the entire Scout application. The route should accept a `POST`
with a JSON body `{ query: string }`, read `LLM_PROVIDER` from env to choose
Anthropic or OpenAI, read the STAC catalog to build the system prompt, call the
selected LLM, and return `{ sql: string, provider: string }`. Test it with
`curl` or a REST client before moving to Phase 3.

**Key things to notice:**

- The route reads the STAC catalog from the filesystem at request time. For
  production, you'd cache this — but for learning, the explicit read makes the
  data flow obvious.
- The `provider` field in the response lets the frontend display which LLM
  produced the SQL — useful for your own debugging and for demonstrating the
  swappable architecture.

The exercise directory contains `01_test_prompt.py` (reads STAC directly from
`scout-phase1-etl/output/`) and `02_build_api_route.md` (guided walkthrough for
the route). The actual API route lives at `src/app/api/scout/query/route.ts`.

### What to Observe

- **The SQL is deterministic (mostly)**: Run the same query twice. LLMs are
  stochastic, but with a well-constrained system prompt and low temperature, the
  output stabilizes quickly. Notice how the category values never drift outside
  the closed vocabulary.
- **Provider comparison**: Run the same query against both Anthropic and OpenAI.
  Are the SQL outputs semantically equivalent? Which one handles ambiguity more
  gracefully? This is a real evaluation exercise that ML engineers do before
  choosing a provider.
- **Token count**: Log the `usage` field from each API response. How many tokens
  does the system prompt consume vs. the user query? This is your cost baseline.
  A longer prompt = higher cost per query.
- **The API contract**: Your route returns `{ sql, provider }`. The frontend in
  Phase 3 depends on this exact shape. Changing the response structure without
  updating the frontend is a breaking change — you've just experienced why API
  contracts matter.

---

## When Prompt Stuffing Breaks Down

The approach in this module works because Scout has one dataset with six columns
and a closed vocabulary of ~30 categories. That's a small, stable knowledge
base.

The architecture breaks when:

- **Many datasets**: A city GIS portal with 50 feature layers, each with
  different schemas, means the context grows past any model's context window.
- **Dynamic schemas**: If new columns or categories are added, someone has to
  manually update the prompt. There's no self-discovery.
- **Cross-dataset queries**: "Show me coffee shops that are inside neighborhoods
  with high foot traffic" requires joining two different data sources — the LLM
  needs to know which sources exist before it can pick them.
- **Ambiguous dataset routing**: "Find vegetation data near my project area" —
  is that parks from the places table? Land cover from a raster source? NDVI
  from a satellite archive?

These are the conditions that justify true **RAG (Retrieval-Augmented
Generation)** with vector embeddings. See the extended modules for how to scale
up: the Vector Schema RAG module covers vector search over schemas and STAC
catalogs, and the Agentic Geo Queries module covers LLM agents that autonomously
select datasets and chain multiple SQL statements.

## Practical Exercises


