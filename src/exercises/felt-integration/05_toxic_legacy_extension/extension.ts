/**
 * Toxic Legacy — AI-Powered Industrial Hazard Proximity Extension
 * ===============================================================
 * A Felt Extension surfacing EPA Superfund and TRI facility data near the
 * current viewport, with a Claude-powered narrative risk summary.
 *
 * SDK surfaces demonstrated:
 *   1. felt.createActionTrigger        — "Analyze Viewport" button
 *   2. felt.createActionTrigger        — "Draw Neighborhood" (polygon AOI)
 *   3. felt.createOrUpdatePanel        — AI narrative panel
 *   4. felt.setTool / onElementCreate  — polygon drawing + AOI query
 *   5. felt.createElement              — facility markers
 *   6. felt.getViewport                — viewport-center analysis
 *   7. felt.getLayers / showLayerDataTable — data table (requires named layer)
 *
 * HOW TO USE:
 *   1. Run `pnpm dev` so http://localhost:3000/api/felt-analyze is live
 *   2. Open any map in Felt → click the bolt icon (App development) in toolbar
 *   3. Click the sparkle icon (Custom extension)
 *   4. Paste this file into the JS code editor → click Run
 *   5. Switch to View mode (extensions only run in View mode)
 *   6. Use "🔍 Analyze Viewport" or "✏️ Draw Neighborhood" in the sidebar
 *
 * DATA SOURCES (all free, CORS-enabled, no auth):
 *   - EPA ECHO API v2:   https://echodata.epa.gov/echo/
 *   - EPA ArcGIS:        https://geopub.epa.gov/ArcGIS/rest/services/EMEF/
 *   - EJScreen API:      https://ejscreen.epa.gov/mapper/ejscreenRESTbroker.aspx
 */

// ── Config ────────────────────────────────────────────────────────────────────

const ANALYZE_URL = "http://localhost:3000/api/felt-analyze";
// Serves Bay Area TRI facilities from a static JSON snapshot.
// A server-side proxy is still needed because Felt runs extensions in a sandboxed
// https iframe that blocks direct http:// calls and requests from null origins.
const FACILITIES_URL = "http://localhost:3000/api/epa-facilities";

const EJSCREEN_BASE = "https://ejscreen.epa.gov/mapper/ejscreenRESTbroker.aspx";

/**
 * BYOK: paste your Anthropic API key here so analyses use your account.
 * The extension code is visible to anyone with map access — use a restricted key.
 * If null, the local dev proxy falls back to ANTHROPIC_API_KEY from .env.local.
 * Deployed (production) instances never use a server key: BYOK is required there.
 *
 * Example: const USER_API_KEY = "sk-ant-api03-...";
 */
const USER_API_KEY = null;

// ── Data Source Registry ──────────────────────────────────────────────────────
//
// To add a new data source to the analysis:
//   1. Write an async fetch function: (lat, lon, radiusMiles) => Feature[]
//      where Feature = { id, name, lat, lon, summary }
//   2. Add an entry to DATA_SOURCES below.
//   3. Nothing else needs to change — analyzeLocation iterates the registry.
//
// Feature shape:
//   id          — unique identifier (string)
//   name        — display name shown on the marker and in the Claude prompt
//   lat / lon   — WGS84 decimal degrees
//   summary     — short string for the marker description and Claude context
//
// Source config shape:
//   id          — machine key (used for marker deduplication)
//   label       — shown in the summary panel
//   contextKey  — label used in the Claude prompt
//   radiusMiles — search radius
//   markerColor — hex color for Place elements
//   fetch       — the fetch function
//   formatContext(items) — formats items[] into a Claude context string
// ─────────────────────────────────────────────────────────────────────────────

// Both TRI and Superfund go through the server-side proxy (static snapshot for TRI;
// Superfund returns empty until a dataset is added). The proxy handles null-origin
// CORS and avoids mixed-content issues from Felt's sandboxed https iframe.
async function fetchFromProxy(lat, lon, radiusMiles, type) {
  const url = new URL(FACILITIES_URL);
  url.searchParams.set("lat", lat.toFixed(5));
  url.searchParams.set("lon", lon.toFixed(5));
  url.searchParams.set("radiusMiles", radiusMiles.toString());
  url.searchParams.set("type", type);
  const resp = await fetch(url.toString());
  if (!resp.ok) return [];
  const data = await resp.json();
  console.log(`[ToxicLegacy] proxy ${type} raw:`, data);
  return data.facilities ?? [];
}

async function fetchTRIFacilities(lat, lon, radiusMiles) {
  return fetchFromProxy(lat, lon, radiusMiles, "TRI");
}

async function fetchSuperfundSites(lat, lon, radiusMiles) {
  return fetchFromProxy(lat, lon, radiusMiles, "NPL");
}

// ── Registered data sources ───────────────────────────────────────────────────
// Add new sources here. The analysis loop handles everything else.

const DATA_SOURCES = [
  {
    id: "tri",
    label: "TRI Facilities",
    contextKey: "TRI facilities (toxic releases)",
    radiusMiles: 3,
    markerColor: "#ef4444",
    fetch: fetchTRIFacilities,
    formatContext: (items) =>
      items.length > 0
        ? items.map((f) => `${f.name} — ${f.summary}`).join("; ")
        : "none found",
  },
  {
    id: "superfund",
    label: "Superfund/NPL Sites",
    contextKey: "Superfund/NPL sites",
    radiusMiles: 5,
    markerColor: "#f97316",
    fetch: fetchSuperfundSites,
    formatContext: (items) =>
      items.length > 0
        ? items.map((f) => `${f.name} (${f.summary})`).join("; ")
        : "none found",
  },
  // ── Extend here ─────────────────────────────────────────────────────────────
  // Example: RCRA hazardous waste sites, air quality monitors, brownfields...
  // {
  //   id: "rcra",
  //   label: "RCRA Hazardous Waste",
  //   contextKey: "RCRA hazardous waste handlers",
  //   radiusMiles: 3,
  //   markerColor: "#a855f7",
  //   fetch: fetchRCRASites,
  //   formatContext: (items) => items.length > 0 ? items.map(f => f.name).join("; ") : "none found",
  // },
];

// ── EJScreen ──────────────────────────────────────────────────────────────────

async function fetchEJScreen(lat, lon) {
  const params = new URLSearchParams({
    namestr: `${lon},${lat}`,
    geometry: "esriGeometryPoint",
    distance: "1",
    unit: "9035",
    areatype: "bufferdist",
    areaid: "0.5",
    f: "json",
  });
  try {
    const resp = await fetch(`${EJSCREEN_BASE}?${params}`);
    if (!resp.ok) return null;
    const data = await resp.json();
    const r = data?.features?.[0]?.attributes;
    if (!r) return null;
    return {
      percentileNatl: Math.round(r.P_PNPL_D2 ?? 0),
      lowIncomePercent: Math.round((r.LOWINCPCT ?? 0) * 100),
      peopleOfColorPercent: Math.round((r.MINORPCT ?? 0) * 100),
    };
  } catch {
    return null;
  }
}

// ── Claude proxy ──────────────────────────────────────────────────────────────

async function askClaude(prompt, context) {
  const body = { prompt, context };
  if (USER_API_KEY) body.apiKey = USER_API_KEY;

  const resp = await fetch(ANALYZE_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) throw new Error(`Proxy error ${resp.status}: ${await resp.text()}`);
  const data = await resp.json();
  return data.response ?? "No response.";
}

// ── Panel helpers ─────────────────────────────────────────────────────────────

const PANEL_ID = await felt.createPanelId();


async function showLoading(title) {
  await felt.createOrUpdatePanel({
    panel: {
      id: PANEL_ID,
      title,
      body: [
          { type: "Text", id: "status", content: "⏳ Querying EPA databases..." },
          { type: "Text", id: "radius-note", content: "_Searches a fixed radius from the viewport center (TRI: 3mi, Superfund: 5mi). Zoom in for localized results._" },
        ],
    },
  });
}

async function showResult(title, sourceResults, narrative, ejData) {
  const ejText = ejData
    ? `**EJScreen (0.5mi):** ${ejData.percentileNatl}th national percentile · ${ejData.lowIncomePercent}% low-income · ${ejData.peopleOfColorPercent}% people of color`
    : "_EJScreen data unavailable_";

  // Build a summary line per source: "3 TRI Facilities · 1 Superfund/NPL Sites"
  const countLine = sourceResults
    .map(({ source, items }) => `**${items.length} ${source.label}**`)
    .join(" · ");

  const totalFound = sourceResults.reduce((n, { items }) => n + items.length, 0);
  const zeroHint =
    totalFound === 0
      ? "\n\n⚠️ _No facilities found. Try zooming into a specific neighborhood or industrial area — analysis runs from the viewport center, so if the map is zoomed out or centered over water, results will be empty._"
      : "";

  await felt.createOrUpdatePanel({
    panel: {
      id: PANEL_ID,
      title,
      body: [
        {
          type: "Text",
          id: "summary",
          content: `${countLine} nearby.${zeroHint}\n\n${ejText}`,
        },
        { type: "Divider", id: "div1" },
        { type: "Text", id: "narrative", content: narrative },
      ],
      // NOTE: felt.showLayerDataTable works on named layers only.
      // Facilities here are individual Place elements, not a layer,
      // so no table button is shown. To enable it, load TRI data via
      // the REST API as a named URL layer instead of createElement calls.
    },
  });
}

// ── Core analysis ─────────────────────────────────────────────────────────────

async function analyzeLocation(lat, lon, label) {
  try {
    await showLoading(`🔍 Analyzing ${label}`);

    // Fetch all registered sources in parallel; failures return [] per source.
    const [sourceResults, ejData] = await Promise.all([
      Promise.all(
        DATA_SOURCES.map(async (source) => {
          const items = await source.fetch(lat, lon, source.radiusMiles).catch((err) => {
            console.warn(`[ToxicLegacy] ${source.id} fetch failed:`, err);
            return [];
          });
          console.log(`[ToxicLegacy] ${source.id}: ${items.length} results`, items);
          return { source, items };
        })
      ),
      fetchEJScreen(lat, lon),
    ]);

    // Build Claude context from the source registry.
    const contextLines = [
      `Location: ${lat.toFixed(4)}, ${lon.toFixed(4)} (${label})`,
      ...sourceResults.map(
        ({ source, items }) =>
          `${source.contextKey} within ${source.radiusMiles}mi: ${source.formatContext(items)}`
      ),
      ejData
        ? `EJScreen: ${ejData.percentileNatl}th national percentile, ${ejData.lowIncomePercent}% low-income, ${ejData.peopleOfColorPercent}% people of color`
        : "EJScreen: unavailable",
    ];

    const narrative = await askClaude(
      "Summarize the environmental health risks for this location in 3–4 sentences. Be specific about facility names and release volumes. Note if this is an environmental justice concern.",
      contextLines.join("\n")
    );

    // Place markers for every feature from every source.
    for (const { source, items } of sourceResults) {
      for (const f of items) {
        try {
          const el = await felt.createElement({
            type: "Place",
            coordinates: [f.lon, f.lat],
            name: f.name,
            description: `${source.label}: ${f.summary}`,
            color: source.markerColor,
          });
          console.log(`[ToxicLegacy] createElement result for "${f.name}":`, el);
        } catch (err) {
          console.error(`[ToxicLegacy] createElement failed for "${f.name}":`, err);
        }
      }
    }

    await showResult(`🏭 Toxic Legacy — ${label}`, sourceResults, narrative, ejData);
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    await felt.createOrUpdatePanel({
      panel: {
        id: PANEL_ID,
        title: "Toxic Legacy",
        body: [{ type: "Text", id: "error-message", content: `❌ Analysis failed: ${msg}` }],
      },
    });
  }
}

// ── Action Trigger 1: Analyze Viewport ───────────────────────────────────────

await felt.createActionTrigger({
  actionTrigger: {
    label: "🔍 Analyze Viewport",
    onTrigger: async () => {
      const viewport = await felt.getViewport();
      const lat = (viewport.bounds[1] + viewport.bounds[3]) / 2;
      const lon = (viewport.bounds[0] + viewport.bounds[2]) / 2;
      await analyzeLocation(lat, lon, "Viewport Center");
    },
  },
});

// ── Action Trigger 2: Draw Neighborhood AOI ──────────────────────────────────

await felt.createActionTrigger({
  actionTrigger: {
    label: "✏️ Draw Neighborhood",
    onTrigger: async () => {
      await felt.setTool("polygon");
      await felt.createOrUpdatePanel({
        panel: {
          id: PANEL_ID,
          title: "Draw Your Neighborhood",
          body: [
            {
              type: "Text",
              id: "instructions",
              content:
                "Draw a polygon on the map to define your area of interest. Analysis runs automatically when you close the shape.",
            },
          ],
        },
      });

      const unsub = felt.onElementCreate({
        handler: async ({ element }) => {
          unsub();
          await felt.setTool(null);
          const geometry = await felt.getElementGeometry(element.id);
          if (!geometry || geometry.type !== "Polygon") return;
          const coords = geometry.coordinates[0];
          const lat = coords.reduce((s, c) => s + c[1], 0) / coords.length;
          const lon = coords.reduce((s, c) => s + c[0], 0) / coords.length;
          await analyzeLocation(lat, lon, "Drawn Neighborhood");
        },
      });
    },
  },
});

// ── Welcome panel ─────────────────────────────────────────────────────────────
// Shown on load so users know where to zoom and what the extension does.

await felt.createOrUpdatePanel({
  panel: {
    id: PANEL_ID,
    title: "🏭 Toxic Legacy",
    body: [
      {
        type: "Text",
        id: "intro",
        content:
          "Surface EPA toxic release (TRI) and environmental justice data near any location in the **San Francisco Bay Area**.",
      },
      { type: "Divider", id: "div-intro" },
      {
        type: "Text",
        id: "how",
        content:
          "**How to use:**\n\n" +
          "1. Zoom into a neighborhood or industrial area\n" +
          "2. Click **🔍 Analyze Viewport** — analysis runs from the map center\n" +
          "3. Or click **✏️ Draw Neighborhood** to define a custom area\n\n" +
          "_Coverage: Bay Area only (lat 37.0–38.5, lon -123.0 to -121.5). Searches a fixed radius from the center point (TRI: 3 mi, Superfund: 5 mi)._",
      },
      { type: "Divider", id: "div-tips" },
      {
        type: "Text",
        id: "test-locations",
        content:
          "**Good test locations:**\n\n" +
          "• **Richmond, CA** — high industrial density near the Bay\n" +
          "• **Oakland Port / Jack London Square** — shipping + industrial\n" +
          "• **San Jose industrial corridor** (N 1st St area)\n" +
          "• **Hayward / Fremont** — manufacturing belt\n\n" +
          "_Zoom to street level before analyzing — viewport center over open water returns zero results._",
      },
    ],
  },
});

console.log("✅ Toxic Legacy loaded. Use the sidebar buttons to begin.");
