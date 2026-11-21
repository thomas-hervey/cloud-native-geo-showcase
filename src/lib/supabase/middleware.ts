import { createServerClient } from "@supabase/ssr";
import type { User } from "@supabase/supabase-js";
import { type NextRequest, NextResponse } from "next/server";
import { getSupabaseConfig } from "./config";

// Vercel kills middleware after 25s. supabase-js retries failed token refreshes
// with exponential backoff, so an unreachable Supabase host can exceed that on
// its own. Cap the whole auth round-trip well below the limit.
export const AUTH_TIMEOUT_MS = 3000;

// ── Public path registry ────────────────────────────────────────────────────
// Paths listed here bypass Supabase session auth and are reachable without
// a logged-in user. When adding a new public API route:
//   1. Add it to PUBLIC_API_ROUTES below.
//   2. Also update the ROUTES array in src/app/api/route.ts — the manifest
//      has its own separate list and will not pick up changes here.
//
// ⚠️  Routes are matched with exact pathname equality. Do NOT use broad
//     prefixes — auth-guard routes by default and opt in deliberately.
// ───────────────────────────────────────────────────────────────────────────

// API routes that are intentionally public (no session required).
// Each entry: [path, reason]
const PUBLIC_API_ROUTES: [string, string][] = [
  ["/api/felt-analyze",   "Called from Felt Extension (sandboxed iframe, null origin). Production: requires the caller's own Anthropic key (BYOK) in the body (401 otherwise). Non-production (local dev): falls back to ANTHROPIC_API_KEY. Rate limited per IP."],
  ["/api/epa-facilities", "Serves static Bay Area TRI snapshot. Called from Felt Extension. No sensitive data."],
  ["/api/readme",         "Serves exercise README files to the tutorial UI — no sensitive data."],
  ["/api/scout/replay",   "Serves recorded Scout runs from src/content/scout-replays. Static files, no LLM call, no sensitive data."],
  ["/api",                "Public API manifest listing all routes and their auth requirements."],
];

export function isPublicPath(pathname: string): boolean {
  return (
    // Next.js internals & static assets
    pathname.startsWith("/_next") ||
    pathname.startsWith("/static") ||
    pathname === "/favicon.ico" ||
    // Auth flow
    pathname.startsWith("/auth/error") ||
    pathname.startsWith("/login") ||
    // Public pages
    pathname === "/" ||
    pathname.startsWith("/cng-modules") ||
    pathname.startsWith("/spatial-eval") ||
    pathname === "/roadmap" ||
    // /scout redirects to /scout/lab, which is gated below
    pathname === "/scout" ||
    // Static media and the self-hosted maplibre worker (not covered by the
    // matcher's image-extension exclusion, e.g. .mp4 and .mjs)
    pathname.startsWith("/assets/") ||
    pathname.startsWith("/maplibre/") ||
    // Scout Lab page is always public: the page itself shows non-admins only the
    // recorded demo, and every live route (/api/scout/*) stays behind login plus
    // getLlmAccess(). Gating the page on LIVE_LLM_ENABLED bounced visitors to /login.
    pathname === "/scout/lab" ||
    // Public API routes — exact match only (see comment above)
    PUBLIC_API_ROUTES.some(([p]) => pathname === p)
  );
}

// @supabase/ssr stores the session as `sb-<project-ref>-auth-token`, chunked
// into `.0`, `.1`, ... when large.
export function hasSupabaseAuthCookie(request: NextRequest): boolean {
  return request.cookies
    .getAll()
    .some(({ name }) => name.startsWith("sb-") && name.includes("-auth-token"));
}

function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(
      () => reject(new Error(`Supabase auth timed out after ${ms}ms`)),
      ms
    );
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timer));
}

function redirectToLogin(request: NextRequest): NextResponse {
  const loginUrl = request.nextUrl.clone();
  loginUrl.pathname = "/login";
  loginUrl.search = "";
  loginUrl.searchParams.set(
    "redirect_to",
    request.nextUrl.pathname + request.nextUrl.search
  );
  return NextResponse.redirect(loginUrl);
}

export async function updateSession(request: NextRequest) {
  let supabaseResponse = NextResponse.next({
    request,
  });

  // Dev bypass — set NEXT_PUBLIC_FEATURE_AUTH_ENABLED=false in .env.local
  if (process.env.NEXT_PUBLIC_FEATURE_AUTH_ENABLED === "false") {
    return supabaseResponse;
  }

  const isPublic = isPublicPath(request.nextUrl.pathname);

  // No session cookie means there is nothing to refresh and no user to find:
  // skip the network call entirely so anonymous traffic never depends on Supabase.
  if (!hasSupabaseAuthCookie(request)) {
    return isPublic ? supabaseResponse : redirectToLogin(request);
  }

  const { url, key } = getSupabaseConfig();

  const supabase = createServerClient(url, key, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value }) =>
          request.cookies.set(name, value)
        );
        supabaseResponse = NextResponse.next({
          request,
        });
        cookiesToSet.forEach(({ name, value, options }) =>
          supabaseResponse.cookies.set(name, value, options)
        );
      },
    },
    cookieOptions: {
      domain:
        process.env.NODE_ENV === "production" ? ".thomashervey.net" : undefined,
      path: "/",
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
    },
  });

  // Refresh the auth token. On timeout or network failure, treat the visitor
  // as signed out: public pages still render (fail open), protected ones go
  // to /login instead of hanging until Vercel returns a 504.
  let user: User | null = null;
  try {
    const { data } = await withTimeout(supabase.auth.getUser(), AUTH_TIMEOUT_MS);
    user = data.user;
  } catch (error) {
    console.error("[middleware] Supabase auth unavailable:", error);
    // Drop any cookies a partial refresh may have queued.
    supabaseResponse = NextResponse.next({ request });
  }

  if (!user && !isPublic) {
    return redirectToLogin(request);
  }

  return supabaseResponse;
}
