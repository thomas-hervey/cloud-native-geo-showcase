# Title: Generate Sample Data for DuckDB-Wasm
# Description: Creates a small parquet file for the browser exercises.

import pandas as pd
import numpy as np
import os

def main():
    # Ensure directory exists
    os.makedirs("data", exist_ok=True)
    
    # Generate 1000 random points with categories
    print("Generating 1000 sample points...")
    n = 1000
    df = pd.DataFrame({
        'id': range(n),
        'lon': np.random.uniform(-122.50, -122.38, n),
        'lat': np.random.uniform(37.72, 37.81, n),
        'category': np.random.choice(['Coffee Shop', 'Park', 'Restaurant', 'Tech Office'], n),
        'score': np.random.uniform(0, 10, n)
    })
    
    output_parquet = "data/places.parquet"
    df.to_parquet(output_parquet, index=False)
    print(f"✅ Created {output_parquet} ({os.path.getsize(output_parquet) / 1024:.1f} KB)")

if __name__ == "__main__":
    main()
