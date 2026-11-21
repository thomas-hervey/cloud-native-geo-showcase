import * as duckdb from '@duckdb/duckdb-wasm';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

import duckdb_wasm from '@duckdb/duckdb-wasm/dist/duckdb-mvp.wasm?url';
import mvp_worker from '@duckdb/duckdb-wasm/dist/duckdb-browser-mvp.worker.js?url';
import duckdb_wasm_eh from '@duckdb/duckdb-wasm/dist/duckdb-eh.wasm?url';
import eh_worker from '@duckdb/duckdb-wasm/dist/duckdb-browser-eh.worker.js?url';

const MANUAL_BUNDLES = {
    mvp: {
        mainModule: duckdb_wasm,
        mainWorker: mvp_worker,
    },
    eh: {
        mainModule: duckdb_wasm_eh,
        mainWorker: eh_worker,
    },
};

let db, conn;
const neighborhoodGeoJSON = {
    "type": "Feature",
    "geometry": {
        "type": "Polygon",
        "coordinates": [[
            [-122.45, 37.75],
            [-122.42, 37.75],
            [-122.42, 37.78],
            [-122.45, 37.78],
            [-122.45, 37.75]
        ]]
    },
    "properties": { "name": "Target Zone" }
};

const map = new maplibregl.Map({
    container: 'map',
    style: 'https://demotiles.maplibre.org/style.json',
    center: [-122.43, 37.77],
    zoom: 12
});

map.on('load', () => {
    map.addSource('neighborhood', { type: 'geojson', data: neighborhoodGeoJSON });
    map.addLayer({
        'id': 'neighborhood-fill',
        'type': 'fill',
        'source': 'neighborhood',
        'paint': { 'fill-color': '#2563eb', 'fill-opacity': 0.2 }
    });
    map.addLayer({
        'id': 'neighborhood-outline',
        'type': 'line',
        'source': 'neighborhood',
        'paint': { 'line-color': '#2563eb', 'line-width': 2 }
    });
});

async function init() {
    const bundle = await duckdb.selectBundle(MANUAL_BUNDLES);
    const worker = new Worker(bundle.mainWorker);
    db = new duckdb.AsyncDuckDB(new duckdb.ConsoleLogger(), worker);
    await db.instantiate(bundle.mainModule, bundle.pthreadWorker);

    document.getElementById('engine-status').textContent = 'Engine: Ready';
    conn = await db.connect();
    
    await setupDuckDB();
}

async function setupDuckDB() {
    const log = document.getElementById('log');
    log.innerHTML += "> Loading spatial extension...<br>";
    
    // 1. Load Spatial Extension
    await conn.query("INSTALL spatial; LOAD spatial;");
    
    // 2. Load Places Data
    log.innerHTML += "> Fetching places.parquet...<br>";
    const response = await fetch('/data/places.parquet');
    const data = new Uint8Array(await response.arrayBuffer());
    await db.registerFileBuffer('places.parquet', data);
    await conn.query("CREATE TABLE places AS SELECT * FROM read_parquet('places.parquet')");

    // 3. Load Neighborhood (Bridge GeoJSON to DuckDB)
    log.innerHTML += "> Registering neighborhood polygon...<br>";
    const neighborhoodWKT = `POLYGON((-122.45 37.75, -122.42 37.75, -122.42 37.78, -122.45 37.78, -122.45 37.75))`;
    await conn.query(`CREATE TABLE neighborhood AS SELECT ST_GeomFromText('${neighborhoodWKT}') as geom`);

    document.getElementById('load-status').textContent = "Everything loaded. Ready to join.";
    document.getElementById('run-btn').disabled = false;
}

async function runJoin() {
    const log = document.getElementById('log');
    const start = performance.now();
    
    log.innerHTML += "> Running Spatial Join...<br>";
    
    const result = await conn.query(`
        SELECT id, lon, lat, category 
        FROM places, neighborhood 
        WHERE ST_Intersects(ST_Point(places.lon, places.lat), neighborhood.geom)
    `);
    
    const rows = result.toArray().map(r => r.toJSON());
    const end = performance.now();
    
    document.getElementById('results-count').textContent = `Found ${rows.length} points in zone!`;
    log.innerHTML += `> Done in ${(end-start).toFixed(1)}ms<br>`;
    
    renderPoints(rows);
}

function renderPoints(points) {
    const geojson = {
        'type': 'FeatureCollection',
        'features': points.map(p => ({
            'type': 'Feature',
            'geometry': { 'type': 'Point', 'coordinates': [p.lon, p.lat] },
            'properties': { 'id': p.id, 'category': p.category }
        }))
    };

    if (map.getSource('results')) {
        map.getSource('results').setData(geojson);
    } else {
        map.addSource('results', { type: 'geojson', data: geojson });
        map.addLayer({
            'id': 'results-layer',
            'type': 'circle',
            'source': 'results',
            'paint': {
                'circle-radius': 6,
                'circle-color': '#ef4444',
                'circle-stroke-width': 2,
                'circle-stroke-color': 'white'
            }
        });
    }
}

document.getElementById('run-btn').addEventListener('click', runJoin);
init();
