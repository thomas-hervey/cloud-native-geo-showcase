# Title: Stream from COG
# Description: Read a specific window from a COG without loading the whole file
import rasterio
from rasterio.windows import Window
import matplotlib.pyplot as plt
import os
from rasterio.plot import show

def main():
    filename = "my_first_cog.tif"
    
    if not os.path.exists(filename):
        print("Please run create_cog.py first!")
        return

    print(f"Opening {filename}...")
    
    with rasterio.open(filename) as src:
        print(f"Full Image Size: {src.width}x{src.height}")
        print(f"Is Tiled? {src.is_tiled}")
        
        # Define a small window (e.g., top-left 200x200 pixels)
        window = Window(col_off=0, row_off=0, width=500, height=500)
        
        print(f"Reading partial window: {window}")
        data = src.read(window=window)
        
        # Display the result
        print("Displaying the 500x500 chip...")
        show(data, title="Partial Read (500x500)")
        
        # Also check overviews
        print(f"Overviews available: {src.overviews(1)}")

if __name__ == "__main__":
    main()