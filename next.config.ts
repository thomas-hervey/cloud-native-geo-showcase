import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow DuckDB-Wasm to use SharedArrayBuffer (required for multi-threaded mode).
  // These headers enable cross-origin isolation for the /scout route.
  async headers() {
    return [
      {
        source: '/scout/:path*',
        headers: [
          { key: 'Cross-Origin-Opener-Policy', value: 'same-origin' },
          { key: 'Cross-Origin-Embedder-Policy', value: 'require-corp' },
        ],
      },
      {
        // The /scout pages are cross-origin isolated (COEP above), so worker scripts
        // must carry COEP themselves or the browser blocks them.
        source: '/maplibre/:path*',
        headers: [
          { key: 'Cross-Origin-Embedder-Policy', value: 'require-corp' },
          { key: 'Cross-Origin-Resource-Policy', value: 'same-origin' },
        ],
      },
      {
        // Allow range requests on Parquet files (critical for partial reads)
        source: '/data/:path*',
        headers: [
          { key: 'Access-Control-Allow-Origin', value: '*' },
          { key: 'Access-Control-Expose-Headers', value: 'Content-Range, Accept-Ranges' },
          { key: 'Cross-Origin-Resource-Policy', value: 'cross-origin' },
        ],
      },
    ];
  },
};

export default nextConfig;
