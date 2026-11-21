"use client";

import dynamic from "next/dynamic";
import { useState } from "react";

// ssr: false ensures @feltmaps/js-sdk is never evaluated on the server.
// "use client" alone is not sufficient with Turbopack — the module is still
// included in the SSR bundle and evaluated in Node.js, where browser globals
// required by the SDK are unavailable.
const FeltEmbed = dynamic(() => import("./FeltEmbed"), { ssr: false });

// Pre-configured map ID from env (optional — allows operator to set a default).
const ENV_MAP_ID = process.env.NEXT_PUBLIC_FELT_MAP_ID ?? "";

/** Extract map ID from a full Felt URL or return the raw value if already an ID. */
function parseMapId(input: string): string {
  const trimmed = input.trim();
  const match = trimmed.match(/felt\.com\/map\/[^?#]*-([A-Za-z0-9]{20,})/);
  if (match) return match[1];
  return trimmed;
}

// ---------------------------------------------------------------------------
// Map ID modal (BYOK — users supply their own map rather than using the demo)
// ---------------------------------------------------------------------------

interface MapIdModalProps {
  open: boolean;
  defaultValue?: string;
  onSave: (mapId: string) => void;
  onSkip?: () => void;
}

function MapIdModal({ open, defaultValue = "", onSave, onSkip }: MapIdModalProps) {
  const [input, setInput] = useState(defaultValue);
  const parsed = parseMapId(input);
  const valid = parsed.length >= 10;

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4 p-6 space-y-4">
        <div>
          <h2 className="text-lg font-bold text-gray-900">Connect your Felt map</h2>
          <p className="text-sm text-gray-500 mt-1">
            Paste your Felt map URL or map ID to embed it here. Annotations you
            draw will be captured by the JS SDK (session-only, not saved to Felt).
          </p>
        </div>

        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-700">
            Felt map URL or ID
          </label>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="https://felt.com/map/My-Map-abc123... or just the ID"
            className={`w-full rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              input && !valid ? "border-red-400" : "border-gray-300"
            }`}
          />
          {input && !valid && (
            <p className="text-xs text-red-500">
              Couldn&apos;t parse a valid map ID — paste the full Felt map URL.
            </p>
          )}
          {input && valid && (
            <p className="text-xs text-gray-400">
              Map ID: <span className="font-mono">{parsed}</span>
            </p>
          )}
        </div>

        <p className="text-xs text-gray-400">
          Find your map URL on <span className="font-medium">felt.com</span> — open
          your map and copy the address bar URL. Map IDs are session-only and never stored.
        </p>

        <div className="flex gap-2 pt-1">
          <button
            onClick={() => onSave(parsed)}
            disabled={!valid}
            className="flex-1 rounded-lg bg-blue-600 text-white text-sm font-medium py-2 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Connect map
          </button>
          {onSkip && (
            <button
              onClick={onSkip}
              className="px-4 rounded-lg border border-gray-200 text-sm text-gray-500 hover:bg-gray-50 transition-colors"
            >
              Skip
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page — owns modal state, delegates embed to FeltEmbed (browser-only)
// ---------------------------------------------------------------------------

export default function FeltDemoPage() {
  const [mapId, setMapId] = useState<string>(ENV_MAP_ID);
  const [showModal, setShowModal] = useState(!ENV_MAP_ID);

  return (
    <>
      <MapIdModal
        open={showModal}
        defaultValue={mapId}
        onSave={(id) => {
          setMapId(id);
          setShowModal(false);
        }}
        onSkip={ENV_MAP_ID ? () => setShowModal(false) : undefined}
      />

      {mapId ? (
        <FeltEmbed
          mapId={mapId}
          onChangeMap={() => setShowModal(true)}
        />
      ) : (
        <div className="flex h-screen items-center justify-center bg-gray-50">
          <div className="text-center space-y-3">
            <p className="text-gray-500 text-sm">No map configured.</p>
            <button
              onClick={() => setShowModal(true)}
              className="text-sm text-blue-600 hover:underline"
            >
              Connect a Felt map
            </button>
          </div>
        </div>
      )}
    </>
  );
}
