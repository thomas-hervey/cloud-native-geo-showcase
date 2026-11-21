import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { checkRateLimit } from '../../lib/rate-limit';

describe('checkRateLimit', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('allows the first request from a new IP', () => {
    expect(checkRateLimit('10.0.0.1')).toBe(true);
  });

  it('allows the 20th consecutive request', () => {
    const ip = '10.0.0.2';
    for (let i = 1; i < 20; i++) checkRateLimit(ip);
    expect(checkRateLimit(ip)).toBe(true); // 20th
  });

  it('denies the 21st request', () => {
    const ip = '10.0.0.3';
    for (let i = 0; i < 20; i++) checkRateLimit(ip);
    expect(checkRateLimit(ip)).toBe(false); // 21st
  });

  it('resets counter after window expires', () => {
    const ip = '10.0.0.4';
    for (let i = 0; i < 20; i++) checkRateLimit(ip);
    expect(checkRateLimit(ip)).toBe(false); // at limit

    vi.advanceTimersByTime(61 * 1000); // advance past 60s window

    expect(checkRateLimit(ip)).toBe(true); // reset, allowed again
  });
});
