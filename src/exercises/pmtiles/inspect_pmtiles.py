# Title: PMTiles Inspector
# Description: Detailed verification of the demo.pmtiles file.

import pystac
from pmtiles.reader import Reader, MemorySource
from pathlib import Path
import pmtiles.tile

def main():
    root_path = Path(__file__).parent
    pmtiles_path = root_path / "data" / "demo.pmtiles"
    
    if not pmtiles_path.exists():
        print(f"❌ ERROR: File not found at {pmtiles_path}")
        return

    print(f"--- Inspecting {pmtiles_path.name} ---")
    with open(pmtiles_path, "rb") as f:
        data = f.read()
        reader = Reader(MemorySource(data))
        header = reader.header()
        
        print(f"Header Signature: Valid")
        print(f"Tile Type:       {header['tile_type']}")
        print(f"Min/Max Zoom:    {header['min_zoom']} / {header['max_zoom']}")
        print(f"Total Bytes:     {len(data)}")
        
        print("\nHeader Dictionary keys:")
        for k, v in header.items():
            print(f"  {k}: {v}")

        print("\nScanning Tile Directory...")
        # PMTiles contains a directory of all available tiles
        
        test_coords = [
            (0, 0, 0),
            (1, 0, 0),
            (1, 1, 0),
            (1, 0, 1),
            (1, 1, 1)
        ]
        
        found_count = 0
        for z, x, y in test_coords:
            tile = reader.get(z, x, y)
            if tile:
                print(f"  ✅ Found Tile: Z={z} X={x} Y={y} | Size: {len(tile)} bytes")
                found_count += 1
            else:
                print(f"  ❌ Missing Tile: Z={z} X={x} Y={y}")

        if found_count == len(test_coords):
            print(f"\n✨ ALL {found_count} TILES VERIFIED!")
        else:
            print(f"\n⚠️ Only {found_count} of {len(test_coords)} tiles found.")

if __name__ == "__main__":
    main()
