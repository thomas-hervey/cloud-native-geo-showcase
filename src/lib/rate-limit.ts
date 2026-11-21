/**
 * A simple in-memory rate limiter to prevent abuse on the API endpoints.
 * Note: Since this is purely in-memory, it resets on server restart and
 * limits are per-instance in serverless environments (like Vercel).
 * For a tutorial app, this is sufficient to prevent simple runaway scripts.
 */

interface RateLimitRecord {
  count: number;
  expiresAt: number;
}

const ipMap = new Map<string, RateLimitRecord>();

// 20 requests per minute per IP
const MAX_REQUESTS = 20;
const WINDOW_MS = 60 * 1000;

export function checkRateLimit(ip: string): boolean {
  const now = Date.now();
  const record = ipMap.get(ip);

  // If no record or expired, reset the window
  if (!record || record.expiresAt < now) {
    ipMap.set(ip, { count: 1, expiresAt: now + WINDOW_MS });
    return true;
  }

  // If over limit, deny
  if (record.count >= MAX_REQUESTS) {
    return false;
  }

  // Otherwise, increment and allow
  record.count += 1;
  return true;
}
