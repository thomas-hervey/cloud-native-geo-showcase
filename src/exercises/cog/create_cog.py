# Title: Create COG
# Description: Convert a standard GeoTIFF to a Cloud Optimized GeoTIFF
import rasterio
from rasterio.io import MemoryFile
from rio_cogeo.cogeo import cog_translate
from rio_cogeo.profiles import cog_profiles
import requests

def main():
    print("Downloading sample Landsat image (this might take a moment)...")
    # We'll use a standard Rasterio test image
    url = "https://raw.githubusercontent.com/rasterio/rasterio/main/tests/data/RGB.byte.tif"
    
    # Download content to memory with status check
    response = requests.get(url)
    response.raise_for_status()
    content = response.content
    
    # Define output filename
    output_filename = "my_first_cog.tif"
    
    print("Converting to COG...")
    
    # Standard COG Profile (Deflate compression is common and efficient)
    dst_profile = cog_profiles.get("deflate")
    
    # In-memory file handling to avoid saving the raw file to disk first
    with MemoryFile(content) as memfile:
        with memfile.open() as src:
            # The cog_translate function handles tiling, overviews, and header ordering
            cog_translate(
                src,
                output_filename,
                dst_profile,
                in_memory=True,
                quiet=False
            )
            
    print(f"Success! Created {output_filename}")
    print("Try running 'rio cogeo validate my_first_cog.tif' in your terminal if you have the CLI installed.")

if __name__ == "__main__":
    main()
