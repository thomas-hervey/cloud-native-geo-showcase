<!-- TODO: Review for expansion - does this module feel too short compared to STAC/Zarr? -->

> [!TIP]
> **Try it out!** You can explore the comparisons discussed in this module on
> the [Spatial Eval Dashboard](/spatial-eval).

> Complete first — the "Richmond bbox" problem encountered there is the direct
> motivation for this investigation.

## Overview

Evaluating LLM geographic knowledge requires designing prompts, ground-truth datasets, and scoring rubrics that measure how well models reason about places, distances, and spatial relationships. The Scout evaluation framework applies this methodology in practice: a structured experiment comparing multiple LLMs on a corpus of San Francisco neighborhoods, scored against authoritative boundary sources including DataSF, OpenStreetMap, and Wikidata. The framework produces spatial metrics (IoU, centroid error) that quantify model accuracy in a way that reveals systematic biases invisible from qualitative inspection.

## Key Concepts

### 1. Evaluation Design

The core question is what to test: topology (does the model's bounding box overlap the official polygon?), distance estimation (how far is the model's centroid from the reference?), and place famousness effects (do models know iconic places better than vernacular ones?). Designing the place corpus across four tiers — from Golden Gate Park to hyper-local vernacular regions like "Mid-Market" — exposes where LLM geographic knowledge degrades and where models agree confidently on a wrong answer.

### 2. Ground-Truth Construction

A spatial QA dataset requires authoritative reference geometries for each place. The framework draws from DataSF (SF Planning Department's official neighborhood boundaries), OpenStreetMap/Nominatim, Wikipedia infobox coordinates, and Wikidata structured geometries. DataSF is the primary source because it provides official polygons — enabling IoU scoring that quantifies accuracy against a legal boundary, not just visual inspection.

### 3. Scoring and Model Comparison

Three primary metrics capture different failure modes: centroid error in meters (is the model's center point correct?), bbox area error as a percentage (does the model's polygon match the reference size?), and Intersection over Union (IoU, where 1.0 is perfect and 0 is no spatial overlap). Aggregating these across models and place tiers produces a model × tier heatmap that reveals which providers know SF best, where knowledge falls off, and whether bigger models are actually better geographers.

When Claude generated `lat BETWEEN 37.773 AND 37.788` for "in the Richmond," it
revealed something interesting: LLMs carry implicit geographic knowledge from
their training on text data, and that knowledge is unaudited, uneven, and
model-dependent. This is why (in part) many organizations are working on
building geo foundational models and world models so that we can explicitly
train on geospatial data to capture geospatial semantic relations, geometry,
topology, etc. not text representations of geographies. This module frames a
structured experiment to measure it.

![Spatial Eval Dashboard](/assets/cng-tutorial-spatial-eval.gif)

## 1. The Research Question

> **Where do LLMs think neighborhoods are?**

Put another way: do different LLMs agree on where a place is (and where it is
not), and how do their answers compare with several reference boundaries?

### Why precision depends on context

How exact a place needs to be depends on what it's used for.

- **Exact boundaries.** In law, property and real estate transactions, zoning
  and administration, a place needs an exact, defensible boundary. A parcel is
  inside a zoning district or it isn't.
- **Vague regions.** In everyday use, geographic research and vernacular
  geography, places like neighborhoods are often vague regions: a recognizable
  core with a fuzzy edge, and boundaries that differ by source. Ask SF
  Planning, OpenStreetMap and Zillow where "the Mission" ends and you get three
  different answers.

So this framework doesn't assume a single ground truth. It compares where
models think places are against multiple reference boundaries, and it measures
how much those references disagree with each other. A low IoU for a place
where the references themselves disagree means something different from a low
IoU for a place with one widely accepted boundary.

More specifically:

- If you ask Claude, GPT-4o, Gemini, Mistral, and Llama the same question ("What
  are the approximate lat/lon bounding box coordinates of the Richmond district
  in San Francisco?"), do they produce the same bbox?
- How does each model's answer compare to the OpenStreetMap polygon for the
  Richmond, or the Wikipedia coordinate, or a crowd-sourced boundary?
- Does model agreement correlate with how famous the place is? (The Richmond vs.
  the Dogpatch vs. the Outer Sunset vs. Visitacion Valley)
- Do models disagree more on **vague** places, informal, socially-constructed
  regions with no official boundary, than on formal administrative boundaries
  like census tracts or ZIP codes?

## 3. Experimental Design

### 3.1 Place corpus

Choose ~modules places at multiple specificity levels and famousness levels:

Tier 1 (Famous, well-defined — easy): Golden Gate Park SF, Chinatown SF, The Castro SF.

Tier 2 (Common, moderately vague — medium): The Richmond SF (the motivating example), The Mission SF, The Tenderloin SF, SoMa (South of Market) SF.

Tier 3 (Local knowledge required — hard): The Dogpatch SF, The Outer Sunset SF, Visitacion Valley SF, Noe Valley SF, Excelsior SF.

Tier 4 (Hyper-local vernacular — very hard, likely high disagreement): "Upper Haight" vs "Lower Haight", "North Beach" (overlaps with Fisherman's Wharf depending on who you ask), "Mid-Market" (an informal planning term, not a neighborhood), "The Panhandle" (a park? A neighborhood around it?).

### 3.2 Models to test

Current default set is defined in `data/models.json`. This central registry
allows models to be toggled on or off without changing code. The registry includes Anthropic (Claude Sonnet 4.6 and Haiku 4.5), OpenAI (GPT-4o and GPT-4o-mini), and Google (Gemini 2.5 Flash). Earlier exploratory runs also covered Gemini 1.5 Pro/Flash and Llama 3.1 8B (via Groq); those are kept in the legacy `results.db` but are not part of the current baseline.

Testing a large and small model from the same provider (Sonnet vs. Haiku, GPT-4o
vs. GPT-4o-mini) measures whether geographic knowledge scales with model size.
To add or remove models, edit the `default` boolean in `data/models.json`, or
explicitly pass `--models` at the command line.

### 3.3 The prompt

The same prompt is sent to all models with no system message: ask for bounding box coordinates of a named place in San Francisco, structured as a JSON object with `centroid_lat`, `centroid_lon`, `bbox_north`, `bbox_south`, `bbox_east`, `bbox_west`, `confidence`, and `notes` fields. Force structured output. Parse with `json.loads`. Flag responses that don't parse or produce obviously impossible coordinates.

Run each model × place pair **3 times** and average the coordinates. LLMs are
stochastic, so a single run may not be representative.

### 3.4 Reference sources

For each place, pull ground-truth data from:

| Source                        | What it provides                                                    | How to access                                                            |
| ----------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| **OpenStreetMap / Nominatim** | Polygon boundary for named places that OSM has mapped               | `geopy.geocoders.Nominatim` or `requests` to nominatim.openstreetmap.org |
| **Wikipedia**                 | Lat/lon coordinate from the article's infobox (if it exists)        | `wikipedia` Python package or Wikipedia API                              |
| **Wikidata**                  | Structured coordinates + bounding box for Wikidata entities         | SPARQL query to `query.wikidata.org`                                     |
| **DataSF**                    | San Francisco's official neighborhood boundaries (SF Planning Dept) | `data.sfgov.org` — GeoJSON download, free                                |

DataSF is particularly valuable: SF has **official** neighborhood boundaries
published by the Planning Department. The Richmond has an official polygon.
Comparing LLM bboxes to the official polygon gives you a quantified accuracy
metric, not just visual inspection.

---

## 4. Analysis

### 4.1 Metrics per place × model

- **Centroid error** (meters): distance from LLM centroid to reference centroid
- **Bbox area error** (%): `|LLM_area - reference_area| / reference_area`
- **IoU (Intersection over Union)**: overlap between LLM bbox polygon and
  reference polygon. IoU = 1 is perfect; 0 is no overlap at all.
- **Parse failure rate**: % of runs where the model returned non-JSON or
  impossible coordinates

### 4.2 Aggregate metrics

- **Model × tier heatmap**: average IoU across models and place tiers, which
  models know more, and where does knowledge fall off?
- **Model agreement surface**: for each place, what is the spread of LLM
  centroids? A tight cluster = high model consensus. A scattered cloud = the
  models disagree. Overlay the reference polygon to see who's right.
- **Size calibration**: LLMs tend to over-estimate how large neighborhoods are
  (they may conflate "the Mission" with "the Mission District" broadly
  construed). Measure bbox area relative to the official polygon area.

### 4.3 The map

The output everyone will understand: for a given place (e.g., "the Richmond"),
draw:

- The official DataSF polygon (ground truth)
- The Wikipedia coordinate (a point)
- The Nominatim result (a polygon, if OSM has it)
- One marker per model, colored by provider
- Ellipses showing the 1-sigma spread of each model's 3 runs

This immediately reveals: which model is most accurate, which is most confident
(tight ellipse), and whether the models cluster together or scatter randomly.

---

## 5. Implementation Sketch

The evaluation directory (`src/exercises/spatial-eval/`) contains five scripts: `01_collect_llm_responses.py` (query all models × all places, save raw JSON), `02_collect_reference_data.py` (pull Nominatim, Wikipedia, Wikidata, DataSF), `03_compute_metrics.py` (IoU, centroid error, parse failure rate), `04_visualize.ipynb` (map, heatmap, scatter plots), plus a `data/` directory for the place corpus, raw LLM outputs, reference geometries, and computed metrics.

Key Python packages: `anthropic` and `openai` for LLM APIs; `geopy.geocoders.Nominatim`, `wikipedia`, and `requests` for reference data; `geopandas`, `shapely.geometry.box`, and `shapely.ops.unary_union` for spatial analysis; `folium`, `pydeck`, `matplotlib`, and `seaborn` for visualization.

---

## 6. Running the Eval Framework

The `src/exercises/spatial-eval/` directory is a complete, runnable
implementation. A top-level dispatcher script (`run.py`) manages the evaluation
commands.

### Setup (one-time)

Set API keys for the providers you are using (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`) in your environment before running any commands.

### First run (full pipeline)

Run these commands in order. Each is idempotent, so re-running is safe and won't
duplicate data.

Populate GT-vs-GT agreement data with `uv run python run.py gt-compare` (run once; re-run only if you add GT sources), then run all models × all 25 places × 3 runs with `uv run python run.py batch-eval`, then launch the dashboard with `uv run streamlit run app.py`.

That's it for a full baseline run. No flags needed, the defaults cover all
models, all places, and the primary GT source (`sf_planning`).

### Test a single place first (Smoke Test)

Before running the full batch (which makes many API calls), smoke-test one
place with `uv run python run.py smoke --place "The Mission" --model "claude-3-5-haiku-latest"`.

### Returning: add new data without re-running everything

All scripts use `INSERT OR REPLACE`, so they skip already-cached LLM responses
and only compute what's missing. You can add a newly-supported model (`--models "gemini/gemini-2.0-flash"`), re-run one place with higher repetition (`--places "Visitacion Valley" --runs 5`), add OSM + Wikidata to the GT agreement matrix (`run.py gt-compare --gt-sources osm wikidata`), or run LLM eval against an additional GT source (`run.py batch-eval --gt-sources osm`).

### View results from the CLI

- Leaderboard ranked by composite score: `uv run python run.py leaderboard --gt-source sf_planning`
- Metric breakdown: `uv run python run.py analysis --metric iou --gt-source sf_planning`
- GT-vs-GT agreement matrix: `uv run python run.py analysis --source-type gt`

### Updating the deployed Streamlit app

`results.db` is committed to git so Streamlit Community Cloud can read
pre-computed results (its filesystem is ephemeral, so scripts cannot run there).
After any local eval run, commit and push the updated DB.

> **TODO (if results grow past ~50 MB):** Migrate away from SQLite-in-git.
> Options: export to Parquet committed to git, or move to Supabase. See `db.py`
> module docstring for the migration path.

### Ground Truth Sources

| Source                    | Key               | Coverage         | Notes                                             |
| ------------------------- | ----------------- | ---------------- | ------------------------------------------------- |
| SF Analysis Neighborhoods | `sf_planning`     | 41 neighborhoods | **Primary** — DataSF official boundaries          |
| Click That Hood           | `click_that_hood` | 37 neighborhoods | Community-sourced; codeforamerica/click_that_hood |
| Zillow (2017)             | `zillow`          | 92 polygons      | 2017 Zillow neighborhood boundaries               |
| OpenStreetMap             | `osm`             | varies           | Live Nominatim query, disk-cached                 |
| Wikidata                  | `wikidata`        | varies           | P3896 geoshape, disk-cached                       |

Query strings for OSM and Wikidata are managed in `data/source_aliases.json`.
Use the **⚙️ Source Config** tab in the Streamlit app to review and edit them.

### Experiments to Try

1. **Compare GT sources**: Run `run_gt_comparison.py` and look at the GT
   Agreement tab. Places where `sf_planning` and `click_that_hood` disagree (low
   IoU) represent genuine semantic ambiguity, so don't penalize LLMs too harshly
   there.

2. **Which model knows SF best?**: Check `leaderboard.py`. Look at both
   composite score and DE-9IM distribution. An "overlaps" relation is much
   better than "disjoint".

3. **Tier analysis**: The corpus has 4 tiers (1 = iconic, 4 = obscure). Do
   models degrade on tier 3–4 places? Run `run_analysis.py --metric composite`
   and look for the pattern.

4. **GT sensitivity**: Run the same model against multiple GT sources. If a
   model scores 0.7 vs `sf_planning` but 0.2 vs `click_that_hood`, the GT
   sources disagree more than the model is wrong.

5. **Add a new GT source**: Create `sources/my_source.py`, decorate with
   `@register_gt("my_source")`, add `from . import my_source` to
   `sources/__init__.py`. It automatically appears in all CLIs and the Streamlit
   app.

---

## 7. What You Might Find (Hypotheses)

Based on what's known about LLM geographic knowledge:

1. **Famousness dominates accuracy.** Golden Gate Park (centroid error < 100m,
   IoU > 0.8 across all models). Visitacion Valley (IoU < 0.3, high variance).

2. **Models agree more than they're right.** For a moderately-famous
   neighborhood, most models will produce similar bboxes. But, all of them may
   be systematically offset or oversized relative to the official polygon. This
   is the most dangerous failure mode: confident consensus on a wrong answer.

3. **Bigger models are not always better geographers.** Geographic knowledge
   depends on training data distribution, not just model capacity. A model
   trained heavily on web text may know more SF neighborhood trivia than a more
   capable model trained on more filtered data.

4. **Models inflate bbox size.** Human descriptions of neighborhoods describe
   the "core" area (the blocks everyone agrees on). LLMs trained on those
   descriptions may overestimate size to be safe. The official polygon may be
   significantly smaller than what any model returns.

5. **High-confidence responses are not more accurate.** The `confidence` field
   in the prompt may not correlate with centroid error. This is testable and
   would be a publishable finding if true.

---

## 7.1 Results so far (March 2026 baseline)

The current baseline is the batch run of 20–21 March 2026: 5 models × 24
active neighborhoods × 3 runs (72 comparisons per model, all parsed), prompt
variant `baseline_v2`, bounding-box answers scored against `sf_planning`.
Values are medians.

| Model             | IoU   | Centroid error | Tier 1 IoU | Tier 2 IoU | Tier 3 IoU | Tier 4 IoU |
| ----------------- | ----- | -------------- | ---------- | ---------- | ---------- | ---------- |
| GPT-4o            | 0.427 | 271 m          | 0.595      | 0.445      | 0.445      | 0.245      |
| Claude Sonnet 4.6 | 0.421 | 304 m          | 0.619      | 0.437      | 0.394      | 0.405      |
| Gemini 2.5 Flash  | 0.359 | 384 m          | 0.576      | 0.449      | 0.419      | 0.255      |
| GPT-4o Mini       | 0.266 | 627 m          | 0.421      | 0.342      | 0.227      | 0.220      |
| Claude Haiku 4.5  | 0.225 | 476 m          | 0.321      | 0.179      | 0.191      | 0.293      |

What the baseline shows:

- **The larger model beat its smaller sibling at both providers that have
  one:** GPT-4o vs. GPT-4o Mini (0.427 vs. 0.266 IoU) and Sonnet 4.6 vs. Haiku
  4.5 (0.421 vs. 0.225).
- **Tier 1 (famous, well-defined places) had the highest median IoU for every
  model.** Below tier 1 the pattern is not a clean decline: GPT-4o and Gemini
  2.5 Flash drop most on tier 4, while Sonnet 4.6 and Haiku 4.5 do about as well
  or better on tier 4 as on tiers 2–3.
- **No model reached a median IoU of 0.5 overall.** A typical answer overlaps
  the SF Planning polygon less than it misses it, so for anything that needs a
  defensible boundary, an LLM's answer needs a reference polygon behind it.

The dashboard at [/spatial-eval](/spatial-eval) shows these medians, and will
show a later re-run side by side with deltas. To record a new period without
touching the baseline, run
`uv run python run.py batch-eval --db duckdb --run-tag 2026-11` (it prefixes
`run_id` and caches responses under `data/llm_responses/2026-11/`), then
`uv run python scripts/export_run_summary.py --db duckdb`.

---

## 8. Connecting This Back to Scout

The direct product implication: if you were to deploy Scout commercially, the
"Richmond problem" is not hypothetical. You could:

- Run this experiment with your target city
- Use the IoU scores to build a **geographic knowledge reliability map**: for
  which neighborhoods can you trust LLM training data? For which do you need to
  supply a polygon?
- Encode that as a product spec: "For neighborhoods with avg model IoU < 0.5, we
  require explicit polygon injection before generating SQL."

This turns a research finding into a concrete engineering requirement.

---

## 9. If You Want to Publish This

The right venue is **ACM SIGSPATIAL** (November, annual). The GeoAI workshop
co-located with SIGSPATIAL is a natural fit for this kind of empirical LLM
evaluation. A 4-page short paper with the map outputs and IoU heatmap would be
competitive.

Prior work to cite and differentiate from:

- Purves et al. on vernacular geography (your comparison source, not prior LLM
  work)
- GeoEval benchmark (you're extending from formal places to vernacular regions)
- Any SIGSPATIAL 2024 papers on LLM spatial reasoning (your experimental setup
  is similar, your corpus of vague/vernacular places is the novelty)
