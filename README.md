# Cloud Native Geospatial Tutorial

> **Read-only showcase snapshot, synced automatically from my working repository.** Some tutorial content, large datasets and private notes are left out, so it will not build as-is.
> Live apps: [Spatial Eval](https://cloud-native-geo-tutorial.thomashervey.net/spatial-eval) · [Scout Lab](https://cloud-native-geo-tutorial.thomashervey.net/scout/lab) · [CNG modules](https://cloud-native-geo-tutorial.thomashervey.net/cng-modules)

A comprehensive, self-directed tutorial on modern Cloud-Native Geospatial
technologies, culminating in building an "Agentic Spatial Hub" called **Scout**.

## Getting Started

### 1. The Curriculum

The content is located in `src/content/modules`. These are Markdown files
explaining the concepts.

- **Start Here**: `src/content/modules/01-introduction.md`
- **Core Formats**: Modules 03 (COG), 04 (Zarr), 05 (Vectors)
- **Data Engineering**: Modules 06 (Iceberg), 07 (Datacubes)

### 2. The Exercises

Hands-on coding is the best way to learn.

- Go to `src/exercises/`.
- Follow the [Exercise README](src/exercises/README.md) to set up your Python
  environment.
- For each module, create a folder (e.g., `src/exercises/03-cog`) and implement
  the code described in the module content.

### 3. The Scout Project (Capstone)

After mastering the basics, you will build **Scout**, a "Chat-to-Map"
application using:

- **Overture Maps** (Data)
- **DuckDB-Wasm** (Client-side SQL)
- **Deck.gl** (Visualization)
- **Next.js** (App)

You will use this repo's Next.js app to build the UI for Scout.

- Run the app: `npm run dev`
- Open http://localhost:3000

## Security

To report a vulnerability, see [SECURITY.md](SECURITY.md). Do not open a
public issue.

Copy `.env.example` to `.env.local` for local development. `.env.local` is for
local use only and must never be committed. Do not put real keys in
`.env.example` or in source code.

## Quick Links

- [Exercise Setup Guide](src/exercises/README.md)
- [Module 03: COG](src/content/modules/03-cog.md)
- [Module 04: Zarr](src/content/modules/04-zarr.md)
- [Module 05: GeoParquet](src/content/modules/05-vector-formats.md)
