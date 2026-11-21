"""
Exercise 1: Felt REST API — Publish Scout Data to a Felt Map
=============================================================
Creates a Felt map, uploads a GeoJSON layer, and applies a Felt Style Language
(FSL) style that colors points by category. Prints the shareable map URL.

Run from src/exercises/:
    uv run python felt-integration/01_rest_api.py

Requires FELT_API_TOKEN in .env.local at project root.
"""

import json
import os
from pathlib import Path

import felt_python
from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[3] / ".env.local")

FELT_API_TOKEN = os.environ["FELT_API_TOKEN"]
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "scout_sample.geojson"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Felt Style Language (FSL) v2.3 — color points by 'category' property.
# categories[] and paint.color[] are parallel arrays (same index = same category).
CATEGORY_FSL = {
    "version": "2.3",
    "type": "categorical",
    "config": {
        "categoricalAttribute": "category",
        "categories": ["park", "food", "landmark", "arts"],
        "showOther": False,
    },
    "paint": {
        "color": ["#4ade80", "#f59e0b", "#818cf8", "#f472b6"],
        "opacity": 1,
    },
}


def create_map(title: str) -> dict:
    print(f"Creating Felt map: '{title}' ...")
    result = felt_python.create_map(title=title, api_token=FELT_API_TOKEN)
    print(f"  Map ID:  {result['id']}")
    print(f"  Map URL: {result['url']}")
    return result


def upload_geojson(map_id: str, geojson_path: Path, layer_name: str) -> dict:
    # API accepts singular file_name (str) and layer_name (str), not lists
    print(f"\nUploading {geojson_path.name} as '{layer_name}' ...")
    result = felt_python.upload_file(
        map_id=map_id,
        file_name=str(geojson_path),
        layer_name=layer_name,
        api_token=FELT_API_TOKEN,
    )
    layer_id = result["layer_id"]
    print(f"  Layer ID: {layer_id}")
    return result


def apply_fsl_style(map_id: str, layer_id: str, fsl: dict) -> None:
    # Correct method is update_layer_style (not update_layer_details)
    print(f"\nApplying FSL style to layer {layer_id} ...")
    felt_python.update_layer_style(
        map_id=map_id,
        layer_id=layer_id,
        style=fsl,
        api_token=FELT_API_TOKEN,
    )
    print("  Style applied.")


def main() -> None:
    print("=" * 60)
    print("Exercise 1: Felt REST API")
    print("=" * 60)

    output_file = OUTPUT_DIR / "felt_map.json"

    if output_file.exists():
        # Idempotent re-run: reuse existing map + layer, only re-apply style.
        # Delete output/felt_map.json to start fresh with a new map.
        state = json.loads(output_file.read_text())
        map_id = state["map_id"]
        map_url = state["map_url"]
        layer_id = state["layer_id"]
        print(f"Map already exists — reusing (delete output/felt_map.json to reset)")
        print(f"  Map ID:   {map_id}")
        print(f"  Layer ID: {layer_id}")
    else:
        map_obj = create_map("Scout SF — Cloud-Native Geo Tutorial")
        map_id = map_obj["id"]
        map_url = map_obj["url"]

        layer = upload_geojson(map_id, FIXTURE_PATH, "SF Places")
        layer_id = layer["layer_id"]

        output_file.write_text(
            json.dumps({"map_id": map_id, "map_url": map_url, "layer_id": layer_id}, indent=2)
        )
        print(f"\n  State saved to: {output_file}")

    apply_fsl_style(map_id, layer_id, CATEGORY_FSL)

    print("\n" + "=" * 60)
    print("Done!")
    print(f"  Map URL: {map_url}")
    print("\nOpen the URL to verify 6 colored SF places appear.")
    print("=" * 60)


if __name__ == "__main__":
    main()
