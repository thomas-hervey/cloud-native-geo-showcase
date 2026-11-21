"""
prepare_data.py — Bay Area TRI Facility Data Prep
==================================================
Downloads EPA Toxic Release Inventory (TRI) facilities for the San Francisco
Bay Area and saves them as a static JSON file used by the /api/epa-facilities
proxy route.

Run once (or annually when EPA refreshes TRI data):

    uv run python felt-integration/05_toxic_legacy_extension/prepare_data.py

Output:
    public/data/bay-area-tri.json

Coverage:
    9-county Bay Area bounding box (lat 37.0–38.5, lon -123.0 to -121.5).
    This is intentionally a static snapshot — not a live API call — so the
    Felt extension works even when EPA APIs are unavailable.

    For full US coverage or production use, swap the static JSON for a
    GeoParquet file queried via DuckDB:
        SELECT * FROM read_parquet('s3://...') WHERE ...

Data source:
    EPA ECHO REST API — two-step flow:
      1. echo_rest_services.get_facilities  → QueryID
      2. echo_rest_services.get_download    → CSV with all fields (incl. FacLong)
    Docs: https://echo.epa.gov/tools/web-services/facility-search-all-data
"""

import json
import sys
from datetime import date
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

# ── Bounding box ──────────────────────────────────────────────────────────────
# 9-county San Francisco Bay Area
LAT_MIN, LAT_MAX = 37.0, 38.5
LON_MIN, LON_MAX = -123.0, -121.5

ECHO_BASE = "https://echodata.epa.gov/echo/"
OUT_PATH = Path(__file__).parents[4] / "public" / "data" / "bay-area-tri.json"


def fetch_query_id() -> str:
    """Step 1 — get a QueryID for TRI facilities in the Bay Area bounding box."""
    url = f"{ECHO_BASE}echo_rest_services.get_facilities"
    params = {
        "output": "JSON",
        "p_c1lat": LAT_MIN,
        "p_c1lon": LON_MIN,
        "p_c2lat": LAT_MAX,
        "p_c2lon": LON_MAX,
        "p_med": "T",       # TRI media program
        "p_trep": "CURR",   # current reporters only
        "responseset": "500",
    }
    print(f"  Querying ECHO get_facilities (bbox: {LAT_MIN},{LON_MIN} → {LAT_MAX},{LON_MAX})…")
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    qid = data["Results"]["QueryID"]
    count = data["Results"].get("QueryRows", "?")
    print(f"  QueryID={qid}, {count} facilities matched")
    return qid


def fetch_facilities_csv(qid: str) -> pd.DataFrame:
    """Step 2a — CSV download (has FacLong, no FacLat)."""
    url = f"{ECHO_BASE}echo_rest_services.get_download"
    params = {"qid": qid, "output": "CSV"}
    print(f"  Downloading CSV for qid={qid} (has FacLong)…")
    resp = requests.get(url, params=params, timeout=60)
    resp.raise_for_status()
    df = pd.read_csv(StringIO(resp.text), low_memory=False)
    print(f"  CSV columns: {df.columns.tolist()}")
    return df


def fetch_facilities_json(qid: str) -> pd.DataFrame:
    """Step 2b — get_qid JSON (has FacLat, no FacLong). Paginate if needed."""
    url = f"{ECHO_BASE}echo_rest_services.get_qid"
    rows = []
    page = 1
    while True:
        params = {"qid": qid, "pageno": page, "output": "JSON"}
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        batch = data.get("Results", {}).get("Facilities", [])
        if not batch:
            break
        rows.extend(batch)
        if len(rows) >= int(data.get("Results", {}).get("QueryRows", 0)):
            break
        page += 1
    df = pd.DataFrame(rows)
    print(f"  JSON columns: {[c for c in df.columns if 'lat' in c.lower() or 'long' in c.lower() or c in ('FacName', 'RegistryID')]}")
    return df


def merge_lat_lon(df_csv: pd.DataFrame, df_json: pd.DataFrame) -> pd.DataFrame:
    """
    EPA ECHO splits coordinates across two endpoints:
      get_download CSV  → FacLong (no FacLat)
      get_qid JSON      → FacLat  (no FacLong)
    Join on RegistryID to get both.
    """
    # Normalize RegistryID to string in both
    df_csv  = df_csv.copy()
    df_json = df_json.copy()
    df_csv["RegistryID"]  = df_csv["RegistryID"].astype(str).str.strip()
    df_json["RegistryID"] = df_json["RegistryID"].astype(str).str.strip()

    # Pull lat + release totals from the JSON side
    json_cols = ["RegistryID", "FacLat"]
    for c in ("TRIReleasesTransfers", "TRIOnSiteReleases"):
        if c in df_json.columns:
            json_cols.append(c)
    lat_df = df_json[json_cols].dropna(subset=["FacLat"])
    merged = df_csv.merge(lat_df, on="RegistryID", how="left")
    print(f"  After merge — rows with FacLat: {merged['FacLat'].notna().sum()} / {len(merged)}")
    return merged


def normalize(df: pd.DataFrame) -> list[dict]:
    """Map raw ECHO CSV columns to the Feature shape the proxy expects."""
    # Field name candidates (ECHO CSV uses mixed casing across versions)
    def col(df: pd.DataFrame, *candidates: str) -> pd.Series | None:
        for c in candidates:
            if c in df.columns:
                return df[c]
            # case-insensitive fallback
            match = [x for x in df.columns if x.lower() == c.lower()]
            if match:
                return df[match[0]]
        return None

    lat_col  = col(df, "FacLat", "Latitude83", "LATITUDE")   # from get_qid JSON
    lon_col  = col(df, "FacLong", "Longitude83", "LONGITUDE", "FacLongitude")  # from get_download CSV
    name_col = col(df, "FacName", "FacilityName", "FACILITY_NAME")
    id_col   = col(df, "RegistryID", "RegistryId", "REGISTRY_ID")
    tri_col  = col(df, "TRIReleasesTransfers", "TRIOnSiteReleases", "TotalReleases")
    city_col = col(df, "FacCity", "CityName", "CITY_NAME")

    if lat_col is None or lon_col is None:
        print("  ⚠️  Could not find lat/lon columns. Available columns:")
        print("  ", df.columns.tolist())
        sys.exit(1)

    facilities = []
    for _, row in df.iterrows():
        try:
            lat = float(row[lat_col.name])
            lon = float(row[lon_col.name])
        except (ValueError, TypeError):
            continue
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            continue

        releases = 0.0
        if tri_col is not None:
            try:
                releases = float(row[tri_col.name])
            except (ValueError, TypeError):
                pass

        facilities.append({
            "id":    str(row[id_col.name])   if id_col   is not None else "",
            "name":  str(row[name_col.name]) if name_col is not None else "Unknown",
            "lat":   round(lat, 6),
            "lon":   round(lon, 6),
            "city":  str(row[city_col.name]) if city_col is not None else "",
            "summary": f"{releases:,.0f} lbs/yr total releases",
        })

    return facilities


def main() -> None:
    print("Bay Area TRI data prep")
    print(f"Output: {OUT_PATH}\n")

    qid      = fetch_query_id()
    df_csv   = fetch_facilities_csv(qid)
    df_json  = fetch_facilities_json(qid)
    df       = merge_lat_lon(df_csv, df_json)

    print(f"\n  Raw rows: {len(df)}")
    facilities = normalize(df)
    print(f"  Normalized facilities with valid coords: {len(facilities)}")

    if not facilities:
        print("  ✗ No facilities with valid coordinates. Exiting.")
        sys.exit(1)

    payload = {
        "metadata": {
            "year":      date.today().year,
            "generated": date.today().isoformat(),
            "source":    "EPA TRI via ECHO REST API (echo_rest_services.get_download)",
            "source_url": "https://echo.epa.gov/tools/web-services/facility-search-all-data",
            "coverage":  "San Francisco Bay Area (lat 37.0–38.5, lon -123.0 to -121.5)",
            "note": (
                "Static snapshot for tutorial use. Refresh annually when EPA updates TRI data. "
                "For production or full-US coverage, replace with a GeoParquet file "
                "queried via DuckDB: SELECT * FROM read_parquet('s3://...') WHERE ..."
            ),
        },
        "facilities": facilities,
    }

    OUT_PATH.write_text(json.dumps(payload, indent=2))
    print(f"\n  ✓ Wrote {len(facilities)} facilities to {OUT_PATH}")


if __name__ == "__main__":
    main()
