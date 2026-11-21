import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const getUser = vi.fn();

vi.mock("@supabase/ssr", () => ({
  createServerClient: () => ({ auth: { getUser } }),
}));

import {
  AUTH_TIMEOUT_MS,
  isPublicPath,
  updateSession,
} from "@/lib/supabase/middleware";

const AUTH_COOKIE = "sb-abcdefghijklmnop-auth-token=stale";

function makeRequest(path: string, cookie?: string): NextRequest {
  return new NextRequest(`https://example.com${path}`, {
    headers: cookie ? { cookie } : {},
  });
}

describe("updateSession", () => {
  beforeEach(() => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://example.supabase.co");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "test-anon-key");
    vi.stubEnv("NEXT_PUBLIC_FEATURE_AUTH_ENABLED", "true");
    vi.spyOn(console, "error").mockImplementation(() => {});
    getUser.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("should_skip_supabase_for_anonymous_visitor_on_public_page", async () => {
    const res = await updateSession(makeRequest("/"));

    expect(getUser).not.toHaveBeenCalled();
    expect(res.headers.get("location")).toBeNull();
  });

  it("should_redirect_anonymous_visitor_on_protected_page_without_network_call", async () => {
    const res = await updateSession(makeRequest("/resources"));

    expect(getUser).not.toHaveBeenCalled();
    expect(res.headers.get("location")).toContain("/login?redirect_to=%2Fresources");
  });

  it("should_fail_open_on_public_page_when_supabase_hangs", async () => {
    vi.useFakeTimers();
    getUser.mockReturnValue(new Promise(() => {}));

    const pending = updateSession(makeRequest("/cng-modules", AUTH_COOKIE));
    await vi.advanceTimersByTimeAsync(AUTH_TIMEOUT_MS);
    const res = await pending;

    expect(res.headers.get("location")).toBeNull();
  });

  it("should_redirect_protected_page_to_login_when_supabase_is_unreachable", async () => {
    getUser.mockRejectedValue(new TypeError("fetch failed"));

    const res = await updateSession(makeRequest("/resources", AUTH_COOKIE));

    expect(res.headers.get("location")).toContain("/login");
  });

  it("should_allow_protected_page_for_signed_in_user", async () => {
    getUser.mockResolvedValue({ data: { user: { id: "u1" } }, error: null });

    const res = await updateSession(makeRequest("/resources", AUTH_COOKIE));

    expect(res.headers.get("location")).toBeNull();
  });
});

describe("isPublicPath", () => {
  it("should_treat_api_routes_as_exact_matches_only", () => {
    expect(isPublicPath("/api")).toBe(true);
    expect(isPublicPath("/api/scout/query")).toBe(false);
  });
});
