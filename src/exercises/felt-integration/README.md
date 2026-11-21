# Felt Integration Exercises

Five exercises covering the Felt developer platform end-to-end.

## Setup

Add to `.env.local` at the project root:
```
FELT_API_TOKEN=felt_pat_...
NEXT_PUBLIC_FELT_MAP_ID=<map ID from Felt dashboard>
```

Exercise 5 also requires editing the `ANALYZE_URL` constant at the top of `05_toxic_legacy_extension/extension.ts` to point to your running proxy (default: `http://localhost:3000/api/felt-analyze`). Locally the proxy uses `ANTHROPIC_API_KEY` from `.env.local`; a deployed instance requires your own key (BYOK) via `USER_API_KEY`.

## Exercises

| File | What It Teaches |
|---|---|
| `01_rest_api.py` | Create maps, upload GeoJSON, style with FSL |
| `02_esri_to_felt.py` | ArcGIS feature service → Felt migration pipeline |
| `03_live_sync.py` | Live data layer + webhook event listener |
| `04_embed_app/` | JS SDK embedding in Next.js, annotation events |
| `05_toxic_legacy_extension/` | Custom Felt Extension with AI panel (EPA hazard data) |

## Running

```bash
cd src/exercises
uv run python felt-integration/01_rest_api.py
uv run python felt-integration/02_esri_to_felt.py
uv run python felt-integration/03_live_sync.py
```

Exercises 4–5: see their own READMEs.
