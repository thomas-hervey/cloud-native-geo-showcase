/**
 * LabMap — DuckDB-Wasm + MapLibre
 * =============================================
 * Like ScoutMap, but uses MapLibre GeoJSON source + layer instead of HTML markers.
 * This is the proper MapLibre approach: dynamic paint properties can be updated
 * in-place without removing/re-adding markers.
 *
 * Key differences from ScoutMap:
 *   - Accepts `layerConfig?: LayerConfig` prop for dynamic styling
 *   - Renders via `map.addSource` + `map.addLayer` (not HTML Marker objects)
 *   - Updates paint properties via `map.setPaintProperty` when layerConfig changes
 *   - Uses `map.on('click', 'results-layer', ...)` for popups
 */

'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { rewriteSqlForWasm, extractParquetUrls, checkParquetReachable } from '@/lib/scout-guards';
import { toCirclePaint, toHeatmapPaint, DEFAULT_LAYER_CONFIG } from '@/lib/scout-layer-config';
import { initDuckDB } from '@/lib/duckdb-client';
import type { DuckDBInstance } from '@/lib/duckdb-client';
import type { LayerConfig, PlaceResult, QueryResult } from '@/lib/scout-types';

export type { PlaceResult, QueryResult };

type MaplibreModule = typeof import('maplibre-gl');

interface LabMapProps {
  onReady: (executeQuery: (sql: string) => Promise<QueryResult>) => void;
  layerConfig?: LayerConfig;
}

interface PlaceRow {
  id: string;
  name: string;
  category: string;
  lat: number;
  lon: number;
}

const SOURCE_ID = 'results';
const LAYER_ID = 'results-layer';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type MapEvent = { features?: GeoJSON.Feature[]; [key: string]: any };

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function LabMap({ onReady, layerConfig }: LabMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const mapRef = useRef<any>(null);
  const duckdbRef = useRef<DuckDBInstance | null>(null);
  const maplibreRef = useRef<MaplibreModule | null>(null);
  // Track current layer type so we know when to remove/re-add the layer
  const currentLayerTypeRef = useRef<'circle' | 'heatmap' | null>(null);
  const [engineStatus, setEngineStatus] = useState<string>('Initializing...');

  // Per-instance event handler refs — stored in useRef so each LabMap instance
  // has its own handler references (avoids module-level variable collisions when
  // two LabMap instances are mounted simultaneously in the split-panel view).
  const handleFeatureClickRef = useRef<((e: MapEvent) => void) | null>(null);
  const handleMouseEnterRef = useRef<(() => void) | null>(null);
  const handleMouseLeaveRef = useRef<(() => void) | null>(null);

  // Always-current layerConfig ref — lets executeQuery (memoized with [] deps)
  // read the latest prop value without going stale.
  const layerConfigRef = useRef(layerConfig);
  useEffect(() => { layerConfigRef.current = layerConfig; }, [layerConfig]);

  // Resolved config — falls back to DEFAULT_LAYER_CONFIG
  const resolvedConfig = layerConfig ?? DEFAULT_LAYER_CONFIG;

  // -----------------------------------------------------------------------
  // Execute a SQL query and render results via GeoJSON source + layer
  // -----------------------------------------------------------------------
  const executeQuery = useCallback(
    async (sql: string): Promise<QueryResult> => {
      const instance = duckdbRef.current;
      const map = mapRef.current;
      const maplibregl = maplibreRef.current;
      if (!instance || !map || !maplibregl) throw new Error('Engine not initialized');

      setEngineStatus('Querying...');

      const rewrittenSql = rewriteSqlForWasm(sql, window.location.origin);

      const parquetRefs = extractParquetUrls(rewrittenSql);
      for (const { url, label } of parquetRefs) {
        await checkParquetReachable(url, label);
      }

      console.log('[LabMap] Executing SQL:', rewrittenSql);

      const result = await instance.conn.query(rewrittenSql);
      const rawRows = result.toArray();

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const rows: PlaceRow[] = rawRows.map((r: any) => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const obj: Record<string, any> = typeof r.toJSON === 'function' ? r.toJSON() : r;
        const height = obj.height != null ? `${Math.round(Number(obj.height))}m` : null;
        return {
          id: String(obj.id ?? obj[0] ?? ''),
          name: String(obj.name ?? obj.nearest_tech_company ?? obj.use_class ?? obj.id ?? ''),
          category: String(obj.category ?? obj.use_class ?? height ?? ''),
          lat: Number(obj.lat ?? obj[3] ?? 0),
          lon: Number(obj.lon ?? obj[4] ?? 0),
        };
      });

      // Build GeoJSON FeatureCollection
      const features: GeoJSON.Feature[] = [];
      for (const row of rows) {
        const lon = Number(row.lon);
        const lat = Number(row.lat);
        if (isNaN(lon) || isNaN(lat)) continue;
        features.push({
          type: 'Feature',
          geometry: { type: 'Point', coordinates: [lon, lat] },
          properties: {
            id: String(row.id ?? ''),
            name: String(row.name ?? ''),
            category: String(row.category ?? ''),
          },
        });
      }

      const geojson: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features };

      const cfg = layerConfigRef.current ?? DEFAULT_LAYER_CONFIG;
      const paintProps = cfg.type === 'heatmap' ? toHeatmapPaint(cfg) : toCirclePaint(cfg);

      // --- Update or create GeoJSON source ---
      if (map.getSource(SOURCE_ID)) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (map.getSource(SOURCE_ID) as any).setData(geojson);
      } else {
        map.addSource(SOURCE_ID, { type: 'geojson', data: geojson });
      }

      // --- Update or create layer ---
      // If the layer type changed (circle ↔ heatmap), remove event handlers then
      // remove the layer. MapLibre does not remove handlers when a layer is removed,
      // so we must call map.off() explicitly to prevent handler accumulation.
      if (map.getLayer(LAYER_ID)) {
        if (currentLayerTypeRef.current !== cfg.type) {
          if (handleFeatureClickRef.current) map.off('click', LAYER_ID, handleFeatureClickRef.current);
          if (handleMouseEnterRef.current) map.off('mouseenter', LAYER_ID, handleMouseEnterRef.current);
          if (handleMouseLeaveRef.current) map.off('mouseleave', LAYER_ID, handleMouseLeaveRef.current);
          handleFeatureClickRef.current = null;
          handleMouseEnterRef.current = null;
          handleMouseLeaveRef.current = null;
          map.removeLayer(LAYER_ID);
        }
      }

      if (!map.getLayer(LAYER_ID)) {
        map.addLayer({
          id: LAYER_ID,
          type: cfg.type,
          source: SOURCE_ID,
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          paint: paintProps as any,
        });
        currentLayerTypeRef.current = cfg.type;

        // Attach click popup (circle layers only — heatmap has no discrete features)
        if (cfg.type === 'circle') {
          handleFeatureClickRef.current = (e: MapEvent) => {
            if (!e.features || e.features.length === 0) return;
            const props = e.features[0].properties ?? {};
            const coords = (e.features[0].geometry as GeoJSON.Point).coordinates as [number, number];
            // Build popup content via DOM (avoids XSS from unescaped prop values)
            const container = document.createElement('div');
            container.style.cssText = 'font-size:13px;line-height:1.5';
            const nameEl = document.createElement('strong');
            nameEl.textContent = String(props.name ?? 'Unknown');
            const br = document.createElement('br');
            const catEl = document.createElement('span');
            catEl.style.color = '#6b7280';
            catEl.textContent = String(props.category ?? '');
            container.append(nameEl, br, catEl);
            new maplibregl.Popup({ closeButton: true, offset: 10 })
              .setLngLat(coords)
              .setDOMContent(container)
              .addTo(map);
          };
          handleMouseEnterRef.current = () => { map.getCanvas().style.cursor = 'pointer'; };
          handleMouseLeaveRef.current = () => { map.getCanvas().style.cursor = ''; };
          map.on('click', LAYER_ID, handleFeatureClickRef.current);
          map.on('mouseenter', LAYER_ID, handleMouseEnterRef.current);
          map.on('mouseleave', LAYER_ID, handleMouseLeaveRef.current);
        }
      } else {
        // Layer exists with same type — update paint properties in place
        for (const [prop, value] of Object.entries(paintProps)) {
          map.setPaintProperty(LAYER_ID, prop, value);
        }
      }

      // Fit map to results
      if (features.length > 0) {
        const bounds = new maplibregl.LngLatBounds();
        features.forEach((f) => {
          const coords = (f.geometry as GeoJSON.Point).coordinates;
          bounds.extend(coords as [number, number]);
        });
        map.fitBounds(bounds, { padding: 60, maxZoom: 16 });
      }

      const count = features.length;
      setEngineStatus(`Ready — ${count} results`);

      const placeResults: PlaceResult[] = features.map((f) => ({
        id: (f.properties?.id as string) ?? '',
        name: (f.properties?.name as string) ?? '',
        category: (f.properties?.category as string) ?? '',
        lon: (f.geometry as GeoJSON.Point).coordinates[0],
        lat: (f.geometry as GeoJSON.Point).coordinates[1],
      }));

      return { count, features: placeResults };
    },
    // layerConfig is read via layerConfigRef (kept current by a useEffect) so
    // this callback does not need layerConfig in its deps.
    []
  );

  // -----------------------------------------------------------------------
  // Re-apply paint properties when layerConfig prop changes between queries
  // -----------------------------------------------------------------------
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.getLayer(LAYER_ID)) return;

    const cfg = layerConfig ?? DEFAULT_LAYER_CONFIG;

    // If layer type changed we can't just update paint — need to swap layers
    if (currentLayerTypeRef.current && currentLayerTypeRef.current !== cfg.type) {
      // Remove event handlers before removing the layer to prevent accumulation
      // of duplicate handlers on subsequent addLayer calls (MapLibre does not
      // remove handlers when a layer is removed).
      if (handleFeatureClickRef.current) map.off('click', LAYER_ID, handleFeatureClickRef.current);
      if (handleMouseEnterRef.current) map.off('mouseenter', LAYER_ID, handleMouseEnterRef.current);
      if (handleMouseLeaveRef.current) map.off('mouseleave', LAYER_ID, handleMouseLeaveRef.current);
      handleFeatureClickRef.current = null;
      handleMouseEnterRef.current = null;
      handleMouseLeaveRef.current = null;
      map.removeLayer(LAYER_ID);
      currentLayerTypeRef.current = null;
      // The layer will be re-added on next executeQuery call
      return;
    }

    const paintProps = cfg.type === 'heatmap' ? toHeatmapPaint(cfg) : toCirclePaint(cfg);
    for (const [prop, value] of Object.entries(paintProps)) {
      try {
        map.setPaintProperty(LAYER_ID, prop, value);
      } catch {
        // Ignore — property may not exist for this layer type
      }
    }
  }, [layerConfig]);

  // -----------------------------------------------------------------------
  // Initialize MapLibre + DuckDB-Wasm on mount
  // -----------------------------------------------------------------------
  useEffect(() => {
    if (!mapContainer.current) return;

    let cancelled = false;
    let mapInstance: InstanceType<MaplibreModule['Map']> | null = null;

    async function init() {
      const maplibregl = await import('maplibre-gl');
      // @ts-expect-error — CSS import works at runtime via bundler
      await import('maplibre-gl/dist/maplibre-gl.css');

      if (cancelled || !mapContainer.current) return;

      maplibreRef.current = maplibregl;
      // maplibre-gl v6 can't find its worker inside a Next.js chunk; see scripts/copy-maplibre-worker.mjs
      maplibregl.setWorkerUrl('/maplibre/maplibre-gl-worker.mjs');

      const map = new maplibregl.Map({
        container: mapContainer.current,
        style: 'https://tiles.openfreemap.org/styles/liberty',
        center: [-122.43, 37.77],
        zoom: 12,
      });
      map.addControl(new maplibregl.NavigationControl(), 'top-right');
      mapRef.current = map;
      mapInstance = map;

      let mapLoaded = false;
      let duckdbReady = false;

      const maybeSignalReady = () => {
        if (cancelled) return;
        if (mapLoaded && duckdbReady) {
          setEngineStatus('Ready');
          onReady(executeQuery);
        }
      };

      map.on('load', () => {
        mapLoaded = true;
        maybeSignalReady();
      });

      setEngineStatus('Loading DuckDB-Wasm...');

      try {
        const instance = await initDuckDB();
        if (cancelled) return;
        duckdbRef.current = instance;
        duckdbReady = true;
        if (!mapLoaded) setEngineStatus('Waiting for map...');
        maybeSignalReady();
      } catch (err) {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : String(err);
        setEngineStatus(`Engine error: ${message}`);
      }
    }

    init();

    return () => {
      cancelled = true;
      mapInstance?.remove();
      void duckdbRef.current?.dispose().catch((e) => console.error('[LabMap] DuckDB dispose failed:', e));
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const isReady = engineStatus === 'Ready' || engineStatus.includes('results');
  const isError = engineStatus.includes('error');

  return (
    <div className="w-full h-full relative">
      <div ref={mapContainer} className="w-full h-full" />

      {/* Engine status badge — same style as ScoutMap */}
      <div className="absolute top-3 left-3 bg-white/90 backdrop-blur-sm rounded-lg px-3 py-1.5 shadow text-sm flex items-center gap-2 z-10">
        <span
          className={`w-2 h-2 rounded-full ${
            isReady ? 'bg-green-500' : isError ? 'bg-red-500' : 'bg-yellow-500 animate-pulse'
          }`}
        />
        <span className="text-gray-700">{engineStatus}</span>
      </div>

      {/* Layer config indicator — shows the current style in the bottom-left */}
      {resolvedConfig.label && (
        <div className="absolute bottom-3 left-3 bg-white/90 backdrop-blur-sm rounded-lg px-2 py-1 shadow text-xs flex items-center gap-1.5 z-10">
          <span
            className="w-3 h-3 rounded-full flex-shrink-0"
            style={{ backgroundColor: `rgb(${resolvedConfig.color.join(', ')})` }}
          />
          <span className="text-gray-600">{resolvedConfig.label}</span>
        </div>
      )}
    </div>
  );
}
