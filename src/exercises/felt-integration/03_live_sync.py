"""
Exercise 3: Live Data Layer + Webhook Event Listener
====================================================
Registers a live data layer (SF 311 GeoJSON feed) with Felt, then starts
a local HTTP server to receive Felt webhook POST events.

Two things to observe:
  1. The live SF 311 layer can be refreshed by calling refresh_url_layer()
  2. When you draw/edit on the map, webhook events print here (requires ngrok)

Note on live refresh: felt_python 0.1.3 does not support automatic polling
intervals via the SDK. `upload_url` registers the URL as a layer and
`refresh_url_layer` triggers a one-shot refresh. Felt's web app UI handles
auto-refresh scheduling. For real-time behavior, call refresh_url_layer()
periodically (see the refresh loop below).

Note on webhooks: felt_python 0.1.3 has no `create_webhook` method. Webhook
registration must be done via the Felt dashboard UI. For Felt to reach your
local server you need a tunnel:
  ngrok http 8765  →  paste HTTPS URL into Felt dashboard > Map Settings > Webhooks

Run from src/exercises/:
    uv run python felt-integration/03_live_sync.py

Requires FELT_API_TOKEN in .env.local at project root.
"""

import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import felt_python
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[3] / ".env.local")

FELT_API_TOKEN = os.environ["FELT_API_TOKEN"]
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# SF 311 cases — open GeoJSON from DataSF (no auth needed)
# Socrata SoQL query params with `$` can trip Felt's URL validator — use the
# bare endpoint and let Felt fetch all records (Socrata defaults to 1000).
LIVE_DATA_URL = "https://data.sfgov.org/resource/vw6y-z8j6.geojson"
WEBHOOK_PORT = 8765
REFRESH_INTERVAL_SECONDS = 60  # how often to poll the URL for new data


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        self.send_response(200)
        self.end_headers()
        try:
            event = json.loads(body)
            print(f"\n[WEBHOOK] {event.get('type', 'event')} received:")
            print(json.dumps(event, indent=2))
        except json.JSONDecodeError:
            print(f"\n[WEBHOOK] Raw: {body.decode()}")

    def log_message(self, format: str, *args) -> None:
        pass  # suppress default request noise


def start_webhook_server(port: int) -> HTTPServer:
    server = HTTPServer(("", port), WebhookHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"  Webhook server listening on :{port}")
    return server


def refresh_loop(map_id: str, layer_id: str, interval: int) -> None:
    """Background thread: trigger a Felt layer refresh every `interval` seconds."""
    while True:
        time.sleep(interval)
        try:
            felt_python.refresh_url_layer(
                map_id=map_id,
                layer_id=layer_id,
                api_token=FELT_API_TOKEN,
            )
            print(f"[REFRESH] Layer {layer_id} refreshed at {time.strftime('%H:%M:%S')}")
        except Exception as exc:
            print(f"[REFRESH] Failed: {exc}")


def main() -> None:
    print("=" * 60)
    print("Exercise 3: Live Data Layer + Webhook Listener")
    print("=" * 60)

    # Reuse an existing map if exercise 1 already created one
    map_ref_path = OUTPUT_DIR / "felt_map.json"
    if map_ref_path.exists():
        with open(map_ref_path) as f:
            ref = json.load(f)
        map_id, map_url = ref["map_id"], ref["map_url"]
        print(f"Using existing map: {map_url}")
    else:
        obj = felt_python.create_map(
            title="SF Live Data Demo",
            api_token=FELT_API_TOKEN,
        )
        map_id, map_url = obj["id"], obj["url"]
        with open(map_ref_path, "w") as f:
            json.dump({"map_id": map_id, "map_url": map_url}, f, indent=2)
        print(f"Created map: {map_url}")

    # Pre-flight: confirm the live data URL is reachable before registering
    print(f"\nChecking live data source ...")
    try:
        probe = requests.get(LIVE_DATA_URL, timeout=15)
        probe.raise_for_status()
        feature_count = len(probe.json().get("features", []))
        print(f"  OK — {feature_count} features available")
    except requests.RequestException as e:
        print(f"  ERROR: Live data URL is unreachable: {e}")
        print(f"  URL: {LIVE_DATA_URL}")
        print("  Check the URL or try a different SF Open Data endpoint.")
        return

    # Register URL layer — felt_python uses `layer_url`, not `url`
    print(f"\nRegistering URL layer from: {LIVE_DATA_URL[:60]}...")
    result = felt_python.upload_url(
        map_id=map_id,
        layer_url=LIVE_DATA_URL,
        layer_name="SF 311 Cases (live)",
        api_token=FELT_API_TOKEN,
    )
    layer_id = result["layer_id"]
    print(f"  Layer registered: {layer_id}")

    # Start periodic refresh thread
    print(f"\nStarting refresh loop (every {REFRESH_INTERVAL_SECONDS}s) ...")
    threading.Thread(
        target=refresh_loop,
        args=(map_id, layer_id, REFRESH_INTERVAL_SECONDS),
        daemon=True,
    ).start()

    # Start local webhook receiver
    print("\nStarting webhook receiver ...")
    server = start_webhook_server(WEBHOOK_PORT)

    # Webhook registration note — felt_python 0.1.3 has no create_webhook()
    print(
        "\n[NOTE] Webhook SDK method not available in felt_python 0.1.3.\n"
        "  Register webhooks via Felt dashboard > Map Settings > Webhooks.\n"
        f"  Point Felt at: http://localhost:{WEBHOOK_PORT}/webhook\n"
        "  (Use 'ngrok http 8765' to expose a public HTTPS URL first.)"
    )

    print("\n" + "=" * 60)
    print(f"Map URL: {map_url}")
    print("\nOpen the map, draw features, watch events print here.")
    print(f"Layer refreshes every {REFRESH_INTERVAL_SECONDS}s automatically.")
    print("Press Ctrl+C to stop.")
    print("=" * 60)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping.")
        server.shutdown()


if __name__ == "__main__":
    main()
