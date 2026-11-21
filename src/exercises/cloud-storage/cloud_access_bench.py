# Title: Cloud Storage Access Patterns
# Description: Demonstrate Range Requests and Requester Pays configuration
import fsspec
import s3fs
import time
import os
import rasterio
from rasterio.session import AWSSession
import boto3
import matplotlib.pyplot as plt

def benchmark_range_request():
    print("--- 1. HTTP RANGE REQUEST BENCHMARK ---")
    # A large Landsat GeoTIFF (~80MB) hosted on Google Cloud Storage
    url = "https://storage.googleapis.com/gcp-public-data-landsat/LC08/01/044/034/LC08_L1TP_044034_20130603_20170310_01_T1/LC08_L1TP_044034_20130603_20170310_01_T1_B4.TIF"
    
    # Method A: Small Range Request
    print("Reading 100 KB from a 80 MB file via Range Request...")
    start = time.time()
    with fsspec.open(url, "rb") as f:
        chunk = f.read(100 * 1024) # 100 KB
    end = time.time()
    print(f"Read {len(chunk)/1024:.1f} KB in {end-start:.4f} seconds")

    # Method B: Larger Range Request
    print("\nReading 5 MB from the same file...")
    start = time.time()
    with fsspec.open(url, "rb") as f:
        chunk = f.read(5 * 1024 * 1024) # 5 MB
    end = time.time()
    print(f"Read {len(chunk)/(1024*1024):.1f} MB in {end-start:.4f} seconds")
    print("Notice how the download time is proportional only to the data you NEED.")

def demonstrate_requester_pays():
    print("\n--- 2. S3 REQUESTER PAYS (CONCEPT) ---")
    # Sentinel-2 L1C on AWS is 'Requester Pays' and located in 'eu-central-1'
    s3_path = "s3://sentinel-s2-l1c/tiles/10/S/DG/2023/6/1/0/B04.jp2"
    
    print(f"Attempting access to {s3_path}...")
    
    # To fix this, you need valid credentials (via aws configure)
    # AND requester_pays=True, AND the correct region
    try:
        # requester_pays=True is the 'I agree to be charged' flag
        fs = s3fs.S3FileSystem(requester_pays=True, client_kwargs={'region_name': 'eu-central-1'}) 
        
        with fs.open(s3_path, "rb") as f:
            chunk = f.read(10)
        print(f"Success! Read {len(chunk)} bytes.")
        
        # Now let's do something more visual!
        visualize_cloud_image(s3_path)
        
    except Exception as e:
        print(f"Caught expected error: {type(e).__name__}")
        print(f"Error details: {e}")
        print("Note: This will still fail until you run 'aws configure' on your machine.")
        print("To fix: Go to IAM -> Create Access Key -> then run 'aws configure' in your terminal.")

def visualize_cloud_image(s3_path):
    print("\n--- 3. VISUALIZING CLOUD DATA (WINDOWED READ) ---")
    print("Pulling a 512x512 crop directly from S3...")
    
    # Rasterio uses boto3 sessions for S3 access
    boto_session = boto3.Session(region_name='eu-central-1')
    
    try:
        # We wrap the open in a Rasterio Env to pass the Requester Pays flag
        with rasterio.Env(AWSSession(boto_session, requester_pays=True)):
            with rasterio.open(s3_path) as src:
                # Read a small 512x512 window from the center of the image
                # This only downloads a few kilobytes/megabytes, not the whole JP2!
                w = src.width // 2
                h = src.height // 2
                window = rasterio.windows.Window(w, h, 512, 512)
                
                # Band 1 is Red
                data = src.read(1, window=window)
                
                plt.figure(figsize=(8, 8))
                plt.imshow(data, cmap='Reds')
                plt.colorbar(label='Reflectance')
                plt.title("Sentinel-2 Red Band (Direct S3 Crop)")
                plt.axis('off')
                
                output_path = "cloud_crop.png"
                plt.savefig(output_path)
                print(f"Success! Saved crop visualization to {os.path.abspath(output_path)}")
    except Exception as e:
        print(f"Visualization failed: {e}")

if __name__ == "__main__":
    benchmark_range_request()
    demonstrate_requester_pays()