/**
 * GET /api/epa-facilities
 *
 * Returns EPA TRI or NPL/Superfund facilities near a lat/lon point.
 * Data is served from a static JSON snapshot (public/data/bay-area-tri.json)
 * rather than live EPA APIs, which have frequent availability issues.
 *
 * To refresh the TRI dataset, run:
 *   uv run python src/exercises/felt-integration/05_toxic_legacy_extension/prepare_data.py
 *
 * Coverage note: Bay Area only (lat 37.0–38.5, lon -123.0 to -121.5).
 * For full-US coverage, replace the JSON file with a GeoParquet queried
 * via DuckDB (@duckdb/node-api):
 *   SELECT * FROM read_parquet('public/data/tri-us.parquet')
 *   WHERE lat BETWEEN ? AND ? AND lon BETWEEN ? AND ?
 *
 * Query params:
 *   lat         — WGS84 latitude  (required)
 *   lon         — WGS84 longitude (required)
 *   radiusMiles — search radius in miles (default 5)
 *   type        — "TRI" or "NPL" (default "TRI"; NPL returns [] — no static dataset yet)
 *
 * Returns: { facilities: Facility[], meta: { total, source, coverage } }
 *
 * Auth: public (called from Felt Extension, null origin)
 */

import { NextRequest, NextResponse } from "next/server";
import path from "path";
import fs from "fs";

// Felt extensions run in a sandboxed iframe — origin is "null".
const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "null",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

interface Facility {
  id: string;
  name: string;
  lat: number;
  lon: number;
  city?: string;
  summary: string;
}

interface DataFile {
  metadata: {
    year: number;
    generated: string;
    source: string;
    coverage: string;
    note: string;
  };
  facilities: Facility[];
}

// Load the static dataset once at module init (cached by Node.js module system).
function loadData(): DataFile | null {
  const filePath = path.join(process.cwd(), "public", "data", "bay-area-tri.json");
  if (!fs.existsSync(filePath)) return null;
  return JSON.parse(fs.readFileSync(filePath, "utf-8")) as DataFile;
}

const DATA = loadData();

/** Convert a lat/lon + radius (miles) to a simple bounding box. */
function toBbox(lat: number, lon: number, radiusMiles: number) {
  const R = 3963.2; // Earth radius in miles
  const latDelta = (radiusMiles / R) * (180 / Math.PI);
  const lonDelta = (radiusMiles / (R * Math.cos((lat * Math.PI) / 180))) * (180 / Math.PI);
  return {
    minLat: lat - latDelta,
    maxLat: lat + latDelta,
    minLon: lon - lonDelta,
    maxLon: lon + lonDelta,
  };
}

export async function OPTIONS() {
  return new NextResponse(null, { status: 204, headers: CORS_HEADERS });
}

export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl;
  const lat = parseFloat(searchParams.get("lat") ?? "");
  const lon = parseFloat(searchParams.get("lon") ?? "");
  const radiusMiles = parseFloat(searchParams.get("radiusMiles") ?? "5");
  const type = (searchParams.get("type") ?? "TRI").toUpperCase();

  if (isNaN(lat) || isNaN(lon)) {
    return NextResponse.json(
      { error: "lat and lon are required numeric parameters" },
      { status: 400, headers: CORS_HEADERS }
    );
  }

  // NPL/Superfund static dataset not yet available — return empty with a note.
  if (type === "NPL") {
    return NextResponse.json(
      {
        facilities: [],
        meta: {
          total: 0,
          note: "Bay Area NPL dataset not yet available. See https://www.epa.gov/superfund for site-level data.",
        },
      },
      { headers: CORS_HEADERS }
    );
  }

  if (!DATA) {
    return NextResponse.json(
      {
        error: "Bay Area TRI dataset not found.",
        hint: "Run: uv run python src/exercises/felt-integration/05_toxic_legacy_extension/prepare_data.py",
      },
      { status: 503, headers: CORS_HEADERS }
    );
  }

  const bbox = toBbox(lat, lon, radiusMiles);
  const facilities = DATA.facilities.filter(
    (f) =>
      f.lat >= bbox.minLat &&
      f.lat <= bbox.maxLat &&
      f.lon >= bbox.minLon &&
      f.lon <= bbox.maxLon
  );

  return NextResponse.json(
    {
      facilities,
      meta: {
        total: facilities.length,
        source: DATA.metadata.source,
        coverage: DATA.metadata.coverage,
        generated: DATA.metadata.generated,
      },
    },
    { headers: CORS_HEADERS }
  );
}
