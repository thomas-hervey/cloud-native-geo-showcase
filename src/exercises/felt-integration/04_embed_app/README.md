# Exercise 4: Felt Embed + JS SDK

This exercise lives in the Next.js app, not as a Python script.

**Files:**
- `src/app/felt-demo/page.tsx` — embedded map page with annotation listener
- `src/app/api/felt-analyze/route.ts` — Claude proxy used by Exercise 5

**Setup:**
1. Add to `.env.local`:
   ```
   NEXT_PUBLIC_FELT_MAP_ID=<your-map-id>
   NEXT_PUBLIC_ANALYZE_URL=http://localhost:3000/api/felt-analyze
   ```
   - `NEXT_PUBLIC_FELT_MAP_ID`: Use the map ID from Exercise 1's `output/felt_map.json`, or create a map in Felt UI.
   - `NEXT_PUBLIC_ANALYZE_URL`: Used by the Toxic Legacy extension in Exercise 5.
2. `pnpm dev`
3. Open http://localhost:3000/felt-demo
4. Select a drawing tool from the toolbar and draw on the map — geometry appears in the sidebar in real time

> **Note:** Annotations drawn via the JS SDK are session-only. They are not persisted back to the Felt map and will not appear on felt.com. This is by design — the SDK's drawing tools are intended for ephemeral overlays (e.g. spatial queries, user selection). The learning objective here is the `onElementCreate` event firing and the geometry being captured in your app.

**The `/api/felt-analyze` route** is a Claude proxy that Exercise 5's extension
calls. Locally it uses `ANTHROPIC_API_KEY` from `.env.local`, so no key lives in
browser-side extension code; on a deployed (production) instance the caller must
send its own key (BYOK) in the request body.
The proxy uses `claude-haiku-4-5-20251001` for fast, low-cost responses.
To switch models, edit the `model` field in `src/app/api/felt-analyze/route.ts`.
