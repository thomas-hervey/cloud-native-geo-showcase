import { createClient } from "@/lib/supabase/server";

/**
 * Single chokepoint for LLM spend. Every route that calls an LLM must check
 * this BEFORE reading an API key or constructing a client.
 *
 * - `live`:   LIVE_LLM_ENABLED=true AND the Supabase user is a super-admin.
 * - `replay`: everything else, including the default when the flag is unset.
 */
export type LlmAccessMode = "live" | "replay";

export interface LlmAccess {
  mode: LlmAccessMode;
}

const SUPER_ADMIN_ROLE = "super-admin";

export async function getLlmAccess(): Promise<LlmAccess> {
  if (process.env.LIVE_LLM_ENABLED !== "true") {
    return { mode: "replay" };
  }

  try {
    const supabase = await createClient();
    const { data } = await supabase.auth.getUser();
    if (data?.user?.app_metadata?.role === SUPER_ADMIN_ROLE) {
      return { mode: "live" };
    }
  } catch (error) {
    console.error("[llm-access] Could not resolve user; defaulting to replay:", error);
  }

  return { mode: "replay" };
}
