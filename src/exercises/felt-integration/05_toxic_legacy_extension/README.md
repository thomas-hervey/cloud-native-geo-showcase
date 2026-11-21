# Exercise 5: "Toxic Legacy" — AI Hazard Proximity Felt Extension

A full Felt Extension that surfaces EPA Toxic Release Inventory (TRI) facility
data near any location in the San Francisco Bay Area and generates a
Claude-powered narrative risk summary.

## Prerequisites

### 1. Environment variables

Add the following to `.env.local` in the project root:

```bash
# Required for local use: the Claude proxy reads this (never used on deployed instances)
ANTHROPIC_API_KEY=sk-ant-...

# Required: Supabase (already set if you've run earlier modules)
NEXT_PUBLIC_SUPABASE_URL=...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
```

Alternatively, set `USER_API_KEY` at the top of `extension.ts` to send your own
Anthropic key (see BYOK section below). A deployed instance always requires this.

### 2. Prepare the Bay Area TRI dataset (run once)

The extension serves facility data from a static Bay Area snapshot rather than
live EPA APIs (which have frequent availability issues). Generate it once:

```bash
cd src/exercises
uv run python felt-integration/05_toxic_legacy_extension/prepare_data.py
```

Output: `public/data/bay-area-tri.json` — 145 EPA TRI facilities across the
9-county Bay Area (lat 37.0–38.5, lon -123.0 to -121.5). Refresh annually when
EPA updates TRI data.

### 3. Start the local dev server

```bash
pnpm dev   # starts http://localhost:3000
```

The extension calls two local API routes:
- `GET /api/epa-facilities` — serves facility data from the static JSON
- `POST /api/felt-analyze` — Claude proxy for narrative generation

Both routes are public (no auth required) and CORS-enabled for Felt's sandboxed
iframe (`origin: null`).

## Loading the Extension

1. Open any map on **felt.com**
2. Click the **bolt icon** (App development) in the toolbar
3. Click the **sparkle icon** (Custom extension)
4. Paste the contents of `extension.ts` into the JS code editor
5. Click **Run**
6. Switch to **View mode** — extensions only run in View mode, not Edit mode

> **Note:** The editor is JavaScript-only. `extension.ts` is written as valid
> JavaScript (no TypeScript syntax) so it pastes cleanly without linting errors.

## Using It

| Sidebar button | What happens |
|---|---|
| **🔍 Analyze Viewport** | Queries TRI + Superfund data near the map center, generates Claude narrative |
| **✏️ Draw Neighborhood** | Activates polygon tool; analysis fires when you close the shape |

**Coverage note:** Data is Bay Area only. Analysis runs from the viewport center
point with a fixed radius (TRI: 3 mi, Superfund: 5 mi). **Zoom to street level**
before analyzing — if the map is zoomed out or the center is over the Bay, you
will get zero results.

**Good test locations:**
- Richmond, CA (near Chevron refinery / industrial waterfront)
- Hayward / Fremont (N 1st St / Mission Blvd manufacturing belt)
- Oakland Port / Jack London Square
- San Jose N 1st St corridor (electronics / semiconductor industry)

## SDK Surfaces Demonstrated

All methods are flat on the `felt` global — no sub-namespaces.

| Method | Purpose |
|---|---|
| `felt.createActionTrigger()` | Sidebar buttons (×2) |
| `felt.createOrUpdatePanel()` | Welcome, loading, and results panels |
| `felt.setTool("polygon")` | AOI drawing mode |
| `felt.onElementCreate()` | AOI completion listener |
| `felt.createElement()` | TRI facility markers |
| `felt.getViewport()` | Viewport-center query |
| `felt.getElementGeometry()` | Polygon centroid for AOI analysis |

## Data Sources

| Source | What it provides | How it's accessed |
|---|---|---|
| EPA TRI (Bay Area snapshot) | Toxic release facilities + lbs/yr releases | Static JSON via `/api/epa-facilities` |
| Superfund/NPL | Hazardous waste cleanup sites | `/api/epa-facilities?type=NPL` (returns empty — no static dataset yet) |
| EJScreen API | Environmental justice percentiles | Direct from `ejscreen.epa.gov` (CORS-enabled) |
| Claude (Haiku) | Narrative risk summary | Via `/api/felt-analyze` (local: server key; deployed: your key) |

## BYOK

Set `USER_API_KEY` at the top of `extension.ts` to use your own Anthropic key:

```javascript
const USER_API_KEY = "sk-ant-api03-...";
```

Use a **restricted key** — the extension code is visible to anyone with map
access. Leave as `null` to use `ANTHROPIC_API_KEY` from `.env.local` when
running locally. On any deployed (production) instance the proxy ignores its
server key, so `USER_API_KEY` is required there (otherwise it returns 401).

## Architecture Notes

- **Static data over live APIs:** EPA's ECHO, FRS, and ArcGIS endpoints have
  frequent availability issues and CORS restrictions from sandboxed iframes.
  The `prepare_data.py` script pre-fetches and merges Bay Area TRI data using a
  two-step ECHO flow (`get_facilities` → QueryID → `get_download` CSV for
  FacLong + `get_qid` JSON for FacLat, merged on RegistryID).

- **DATA_SOURCES registry:** The extension iterates a `DATA_SOURCES` array
  rather than hardcoding fetch logic per source. Adding RCRA hazardous waste,
  air quality monitors, or brownfields is one config block — no logic changes.

- **Local proxy, BYOK in production:** Locally the extension holds no key and
  `/api/felt-analyze` uses `ANTHROPIC_API_KEY` from `.env.local`. On a deployed
  instance (`NODE_ENV=production`) the proxy never uses a server key; the
  extension must send its own key in the POST body via `USER_API_KEY`.

## Production Notes

- Replace `ANALYZE_URL` / `FACILITIES_URL` with your deployed endpoint URLs
- `/api/felt-analyze` is rate limited per IP and requires a BYOK `apiKey` in production; add rate limiting to any other public proxy routes
- To enable a data table view, load TRI data via the REST API as a named URL
  layer instead of `createElement` calls (`felt.showLayerDataTable` requires a
  named layer, not individual Place elements)
- For full-US coverage, replace the static JSON with a GeoParquet file queried
  via DuckDB: `SELECT * FROM read_parquet('public/data/tri-us.parquet') WHERE ...`
