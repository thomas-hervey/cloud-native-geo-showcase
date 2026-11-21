import * as duckdb from '@duckdb/duckdb-wasm';
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

let db;
let conn;

async function initDuckDB() {
    // Select the bundle based on environment capabilities
    const bundle = await duckdb.selectBundle(MANUAL_BUNDLES);
    const worker = new Worker(bundle.mainWorker);
    const logger = new duckdb.ConsoleLogger();
    db = new duckdb.AsyncDuckDB(logger, worker);
    await db.instantiate(bundle.mainModule, bundle.pthreadWorker);

    document.getElementById('engine-status').textContent = 'Engine: Ready';
    document.getElementById('engine-status').style.background = '#dcfce7';
    document.getElementById('engine-status').style.color = '#166534';
    
    conn = await db.connect();
    await loadData();
}

async function loadData() {
    document.getElementById('data-status').textContent = 'Data: Loading...';
    
    // Fetch the local parquet file
    const response = await fetch('/data/places.parquet');
    const arrayBuffer = await response.arrayBuffer();
    await db.registerFileBuffer('places.parquet', new Uint8Array(arrayBuffer));
    
    // Map the file to a table
    await conn.query(`CREATE TABLE places AS SELECT * FROM read_parquet('places.parquet')`);
    
    document.getElementById('data-status').textContent = 'Data: places.parquet loaded';
    document.getElementById('data-status').style.background = '#dcfce7';
    document.getElementById('data-status').style.color = '#166534';
}

async function runQuery() {
    const sql = document.getElementById('sql-input').value;
    const start = performance.now();
    
    try {
        const result = await conn.query(sql);
        const end = performance.now();
        
        document.getElementById('query-time').textContent = `Query completed in ${(end - start).toFixed(2)}ms`;
        renderResults(result);
    } catch (err) {
        console.error(err);
        alert('SQL Error: ' + err.message);
    }
}

function renderResults(result) {
    const header = document.getElementById('table-header');
    const body = document.getElementById('table-body');
    
    header.innerHTML = '';
    body.innerHTML = '';
    
    if (result.length === 0) return;

    // Render Header
    const schema = result.schema.fields;
    schema.forEach(field => {
        const th = document.createElement('th');
        th.textContent = field.name;
        header.appendChild(th);
    });

    // Render Rows
    result.toArray().forEach(row => {
        const tr = document.createElement('tr');
        row = row.toJSON();
        schema.forEach(field => {
            const td = document.createElement('td');
            td.textContent = row[field.name];
            tr.appendChild(td);
        });
        body.appendChild(tr);
    });
}

document.getElementById('run-btn').addEventListener('click', runQuery);

// Start Initialization
initDuckDB();
