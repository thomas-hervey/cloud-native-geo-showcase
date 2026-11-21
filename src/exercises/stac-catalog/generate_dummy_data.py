import rasterio
from rasterio.transform import from_origin
import numpy as np
import os
from pathlib import Path

def create_dummy_cog(path, lon, lat):
    data = np.zeros((10, 10), dtype='uint8')
    transform = from_origin(lon, lat, 0.01, 0.01)
    with rasterio.open(path, 'w', driver='GTiff', 
                      height=10, width=10, count=1, 
                      dtype='uint8', crs='EPSG:4326', 
                      transform=transform) as dst:
        dst.write(data, 1)
    print(f"Created {path}")

def main():
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    create_dummy_cog(data_dir / "scene_01.tif", -122.5, 37.8)
    create_dummy_cog(data_dir / "scene_02.tif", -122.4, 37.7)

if __name__ == "__main__":
    main()
