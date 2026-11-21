"""
Exercise 2: Esri-to-Felt Migration Pipeline
============================================
Pulls features from a public ArcGIS REST feature service (SF street trees),
and publishes to Felt with a green FSL style.

SE talking point: replaces manual Export → ZIP → Upload workflow.
Can be scheduled to keep Felt in sync with Esri enterprise data.

Run from src/exercises/:
    uv run python felt-integration/02_esri_to_felt.py

Requires FELT_API_TOKEN in .env.local at project root.
"""

import json
import os
from pathlib import Path

import felt_python
import geopandas as gpd
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[3] / ".env.local")

FELT_API_TOKEN = os.environ["FELT_API_TOKEN"]
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Primary: SF DPW ArcGIS Feature Service
ARCGIS_URL = (
    "https://services.sfgov.org/arcgis/rest/services/DPW/TreeMaintenance"
    "/FeatureServer/0/query"
)
# Fallback: SF Open Data (Socrata) — same dataset, different host
SOCRATA_URL = "https://data.sfgov.org/resource/tkzw-k3nq.geojson"

# FSL v2.3 simple point style
TREE_FSL = {
    "version": "2.3",
    "type": "simple",
    "paint": {
        "color": "#22c55e",
        "size": 4,
        "opacity": 0.8,
    },
}


def fetch_arcgis_features(url: str, max_features: int = 500) -> gpd.GeoDataFrame:
    params = {
        "where": "1=1",
        "outFields": "TreeID,qSpecies,qSiteInfo,qCaretaker",
        "returnGeometry": "true",
        "f": "geojson",
        "resultRecordCount": max_features,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    gdf = gpd.GeoDataFrame.from_features(data["features"])
    return gdf.set_crs("EPSG:4326", allow_override=True)


def fetch_socrata_features(url: str, max_features: int = 500) -> gpd.GeoDataFrame:
    resp = requests.get(url, params={"$limit": max_features}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    gdf = gpd.GeoDataFrame.from_features(data["features"])
    return gdf.set_crs("EPSG:4326", allow_override=True)


def fetch_trees(max_features: int = 500) -> gpd.GeoDataFrame:
    """Fetch SF street trees, falling back to Socrata if ArcGIS is unavailable."""
    print(f"Fetching up to {max_features} SF street trees ...")
    try:
        print(f"  Source: ArcGIS ({ARCGIS_URL})")
        gdf = fetch_arcgis_features(ARCGIS_URL, max_features)
        print(f"  Retrieved {len(gdf)} features via ArcGIS")
        return gdf
    except requests.RequestException as e:
        print(f"  ArcGIS unavailable ({e})")
        print(f"  Falling back to SF Open Data / Socrata ({SOCRATA_URL})")
        gdf = fetch_socrata_features(SOCRATA_URL, max_features)
        print(f"  Retrieved {len(gdf)} features via Socrata")
        return gdf


def main() -> None:
    print("=" * 60)
    print("Exercise 2: Esri-to-Felt Migration Pipeline")
    print("=" * 60)

    map_ref_path = OUTPUT_DIR / "felt_map.json"
    if map_ref_path.exists():
        with open(map_ref_path) as f:
            ref = json.load(f)
        map_id, map_url = ref["map_id"], ref["map_url"]
        print(f"Using existing map: {map_url}")
    else:
        print("No Exercise 1 map found — creating new map ...")
        obj = felt_python.create_map(
            title="SF Street Trees — Esri Migration Demo",
            api_token=FELT_API_TOKEN,
        )
        map_id, map_url = obj["id"], obj["url"]
        with open(map_ref_path, "w") as f:
            json.dump({"map_id": map_id, "map_url": map_url}, f, indent=2)

    gdf = fetch_trees()
    geojson_path = OUTPUT_DIR / "sf_street_trees.geojson"
    gdf.to_file(geojson_path, driver="GeoJSON")
    print(
        f"  GeoJSON written: {geojson_path.name}"
        f"  ({geojson_path.stat().st_size / 1024:.1f} KB)"
    )

    print(f"\nUploading to Felt map {map_id} ...")
    # upload_file takes a single file_name (str) and layer_name (str)
    result = felt_python.upload_file(
        map_id=map_id,
        file_name=str(geojson_path),
        layer_name="SF Street Trees (from ArcGIS)",
        api_token=FELT_API_TOKEN,
    )
    layer_id = result["layer_id"]
    felt_python.update_layer_style(
        map_id=map_id,
        layer_id=layer_id,
        style=TREE_FSL,
        api_token=FELT_API_TOKEN,
    )
    print("  Uploaded and styled.")

    print("\n" + "=" * 60)
    print("Done! SF street trees now live in Felt alongside Scout places.")
    print(f"Map URL: {map_url}")
    print("\nSE talking point: This script replaces a manual Export → ZIP → Upload")
    print("workflow and can be scheduled to keep Felt in sync with Esri data.")
    print("=" * 60)


if __name__ == "__main__":
    main()
