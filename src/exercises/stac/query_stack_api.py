# Title: Query STAC API
# Description: Connect to and query the Microsoft Planetary Computer STAC API

import pystac_client
import planetary_computer
import matplotlib.pyplot as plt
import requests
from PIL import Image
from io import BytesIO
import os

def main():
    try:
        print("Connecting to Microsoft Planetary Computer STAC API...")
        # Connect to Microsoft Planetary Computer STAC API
        catalog = pystac_client.Client.open(
            "https://planetarycomputer.microsoft.com/api/stac/v1",
            modifier=planetary_computer.sign_inplace
        )

        print("Searching for Landsat 8 scenes over San Francisco from 2021...")
        # Search for Landsat 8 scenes over San Francisco from 2021
        search = catalog.search(
            collections=["landsat-8-c2-l2"],
            bbox=[-122.5, 37.5, -122.0, 38.0],  # San Francisco area
            datetime="2021-06-01/2021-07-01",
            query={"eo:cloud_cover": {"lt": 10}}  # Less than 10% cloud cover
        )

        # Get the first item from the search results
        items = list(search.get_items())
        if not items:
            print("No items found matching the search criteria.")
            return

        item = items[0]
        print(f"Found item: {item.id}")


        # Print some information about the item
        print(f"Date: {item.datetime}")
        print(f"Geometry: {item.geometry['type']}")
        print(f"Available assets: {', '.join(list(item.assets.keys())[:10])}...")
        if len(item.assets) > 10:
            print(f"(and {len(item.assets) - 10} more assets)")

        print("item.assets.keys(): ", list(item.assets.keys()))
        print(item)

        # Access and visualize a band (true color composite)
        if "rendered_preview" in item.assets:
            visual_asset = item.assets["rendered_preview"]
            print(f"Downloading preview image: {visual_asset.href}")

            # Sign the URL if needed (for Planetary Computer)
            visual_url = visual_asset.href

            try:
                # Download and save the image
                response = requests.get(visual_url)
                if response.status_code == 200:
                    img = Image.open(BytesIO(response.content))
                    
                    # Save the image
                    output_file = 'landsat_preview.png'
                    img.save(output_file)
                    print(f"Preview image saved as '{output_file}'")
                    
                    # Display basic image information
                    print(f"Image size: {img.size}")
                    print(f"Image mode: {img.mode}")
                else:
                    print(f"Failed to download image: HTTP {response.status_code}")
            except Exception as e:
                print(f"Error processing image: {e}")
        else:
            print("No rendered preview available for this item.")
            
        # Print some metadata about the item
        print("\nItem metadata:")
        for key, value in item.properties.items():
            if key.startswith("eo:") or key.startswith("landsat:"):
                print(f"  {key}: {value}")

        print("\nTo explore more STAC APIs, you can try:")
        print("- NASA CMR STAC: https://cmr.earthdata.nasa.gov/stac/")
        print("- Element84 Earth Search: https://earth-search.aws.element84.com/v0")
        print("- Google Earth Engine STAC: https://earthengine-stac.storage.googleapis.com/catalog/catalog.json")


    except Exception as e:
        print(f"Error: {e}")
        return

if __name__ == "__main__":
    main()