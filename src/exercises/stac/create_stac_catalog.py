# Title: Create STAC Catalog
# Description: Create a basic STAC catalog structure using PySTAC

import os
import json
import datetime
from pathlib import Path
import pystac
from shapely.geometry import box

# Create a directory for our STAC catalog
output_dir = Path("simple_stac_catalog")
output_dir.mkdir(exist_ok=True)

# Create a catalog
catalog = pystac.Catalog(
    id="simple-stac-catalog",
    description="A simple STAC catalog for learning purposes",
    title="Simple STAC Catalog"
)

# Create a collection
collection = pystac.Collection(
    id="landsat-collection",
    description="A simple collection of Landsat imagery",
    extent=pystac.Extent(
        spatial=pystac.SpatialExtent([[-180, -90, 180, 90]]),
        temporal=pystac.TemporalExtent([[datetime.datetime.now(), None]])
    ),
    title="Landsat Collection"
)

# Add the collection to the catalog
catalog.add_child(collection)

# Create a sample STAC item
item = pystac.Item(
    id="landsat-scene-1",
    geometry=box(-122.5, 37.5, -122.0, 38.0).__geo_interface__,
    bbox=[-122.5, 37.5, -122.0, 38.0],
    datetime=datetime.datetime.now(),
    properties={}
)

# Add a sample asset (this would be a link to an actual image file in a real scenario)
item.add_asset(
    "image",
    pystac.Asset(
        href="https://people.math.sc.edu/Burkardt/data/tif/at3_1m4_01.tif",
        media_type="image/tiff; application=geotiff",
        roles=["data"]
    )
)

# Add the item to the collection
collection.add_item(item)

# Save the catalog
catalog.normalize_and_save(str(output_dir))

print(f"STAC catalog created at {output_dir.absolute()}")

# Print a summary of what was created
print("\nCatalog Structure:")
print(f"- Catalog: {catalog.id}")
print(f"  - Collection: {collection.id}")
print(f"    - Item: {item.id}")
print(f"      - Asset: image")

# Print instructions for exploring the catalog
print("\nTo explore the catalog, you can:")
print("1. Navigate through the JSON files in the simple_stac_catalog directory")
print("2. Use a STAC browser to visualize it (e.g., https://radiantearth.github.io/stac-browser/)")
print("3. Use PySTAC to programmatically explore it:")
print("   loaded_catalog = pystac.Catalog.from_file('simple_stac_catalog/catalog.json')")
