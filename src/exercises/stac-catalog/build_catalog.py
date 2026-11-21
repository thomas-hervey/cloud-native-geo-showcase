# Title: Automated STAC Catalog Builder
# Description: Simulates an ETL step that crawls a directory and registers items in a STAC catalog.

import os
import datetime
from pathlib import Path
import rasterio
from rasterio.warp import transform_bounds
import pystac
from pystac.extensions.eo import EOExtension
from pystac.extensions.projection import ProjectionExtension
from shapely.geometry import box, mapping

def get_metadata(tif_path):
    """Extract spatial and temporal metadata from a GeoTIFF."""
    with rasterio.open(tif_path) as src:
        bounds = src.bounds
        crs = src.crs.to_string()
        
        # If not in EPSG:4326, reproject bounds for STAC
        if src.crs.to_string() != "EPSG:4326":
            w, s, e, n = transform_bounds(src.crs, "EPSG:4326", *bounds)
        else:
            w, s, e, n = bounds
            
        bbox = [w, s, e, n]
        geometry = mapping(box(w, s, e, n))
        
        # In a real pipeline, these would come from the sensor metadata
        # Here we simulate with file modification time
        timestamp = datetime.datetime.fromtimestamp(os.path.getmtime(tif_path))
        
        return {
            "bbox": bbox,
            "geometry": geometry,
            "datetime": timestamp,
            "crs": crs,
            "shape": [src.height, src.width]
        }

def main():
    catalog_id = "automation-lab-catalog"
    root_path = Path(__file__).parent
    data_path = root_path / "data"
    output_path = root_path / "stac_catalog"
    
    print(f"Initializing STAC Catalog: {catalog_id}")
    catalog = pystac.Catalog(
        id=catalog_id,
        description="A catalog generated automatically from a directory of COGs.",
        title="Automated Production Catalog"
    )

    # Create a Collection
    collection_id = "processed-imagery"
    print(f"Creating Collection: {collection_id}")
    
    # We'll update the extent as we add items
    extent = pystac.Extent(
        spatial=pystac.SpatialExtent([[0, 0, 0, 0]]),
        temporal=pystac.TemporalExtent([[datetime.datetime.now(), None]])
    )
    
    collection = pystac.Collection(
        id=collection_id,
        description="A group of items processed by our simulated ETL pipeline.",
        extent=extent,
        title="Processed Imagery Collection"
    )
    catalog.add_child(collection)

    # 1. Crawl the directory
    tifs = list(data_path.glob("*.tif"))
    print(f"Found {len(tifs)} files to catalog.")

    items = []
    spatial_extents = []
    temporal_extents = []

    for tif in tifs:
        print(f"  Processing {tif.name}...")
        meta = get_metadata(tif)
        
        # Create the STAC Item
        item = pystac.Item(
            id=tif.stem,
            geometry=meta["geometry"],
            bbox=meta["bbox"],
            datetime=meta["datetime"],
            properties={}
        )
        
        # Add Projection Extension
        proj = ProjectionExtension.ext(item, add_if_missing=True)
        proj.epsg = int(meta["crs"].split(":")[-1])
        proj.shape = meta["shape"]
        
        # Add the Asset
        # In production, this would be an S3 URL
        item.add_asset(
            "data",
            pystac.Asset(
                href=f"./data/{tif.name}",
                media_type=pystac.MediaType.GEOTIFF,
                roles=["data", "visual"]
            )
        )
        
        collection.add_item(item)
        items.append(item)
        spatial_extents.append(meta["bbox"])
        temporal_extents.append(meta["datetime"])

    # 2. Update Collection Extent
    if spatial_extents:
        # Calculate global bbox
        min_x = min(e[0] for e in spatial_extents)
        min_y = min(e[1] for e in spatial_extents)
        max_x = max(e[2] for e in spatial_extents)
        max_y = max(e[3] for e in spatial_extents)
        
        min_t = min(temporal_extents)
        max_t = max(temporal_extents)
        
        collection.extent = pystac.Extent(
            spatial=pystac.SpatialExtent([[min_x, min_y, max_x, max_y]]),
            temporal=pystac.TemporalExtent([[min_t, max_t]])
        )

    # 3. Save the Catalog (Normalized)
    print(f"Saving catalog to {output_path}...")
    catalog.normalize_and_save(str(output_path), catalog_type=pystac.CatalogType.SELF_CONTAINED)

    # 4. Validation
    print("\nValidating catalog...")
    try:
        catalog.validate_all()
        print("✅ SUCCESS: Catalog is valid STAC!")
    except Exception as e:
        print(f"❌ VALIDATION ERROR: {e}")

    print("\nLab Complete.")
    print("Next Step: Use a STAC browser or 'PySTAC.from_file()' to load the results.")

if __name__ == "__main__":
    main()
