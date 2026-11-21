// maplibre-gl v6 resolves its worker relative to the bundle URL
// (`./maplibre-gl-worker.mjs`). Next.js bundles the library into a hashed chunk,
// so that URL 404s and the map never loads. Serve the worker from /maplibre/
// and point maplibre at it with setWorkerUrl().
import { copyFileSync, mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";

const require = createRequire(import.meta.url);
const pkgDir = dirname(require.resolve("maplibre-gl/package.json"));
const outDir = join(process.cwd(), "public", "maplibre");

mkdirSync(outDir, { recursive: true });
copyFileSync(
  join(pkgDir, "dist", "maplibre-gl-worker.mjs"),
  join(outDir, "maplibre-gl-worker.mjs"),
);
console.log("copied maplibre-gl-worker.mjs to public/maplibre/");
