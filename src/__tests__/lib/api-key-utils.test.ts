import { describe, it, expect } from 'vitest';
import { detectProvider, validateKeyForProvider } from '@/lib/api-key-utils';

describe('detectProvider', () => {
  it('detects Anthropic from sk-ant-api03- prefix', () => {
    expect(detectProvider('sk-ant-api03-abc123')).toBe('claude');
  });

  it('detects OpenAI from sk- prefix (non-ant)', () => {
    expect(detectProvider('sk-proj-abc123')).toBe('openai');
    expect(detectProvider('sk-abc123')).toBe('openai');
  });

  it('returns invalid for unrecognised prefixes', () => {
    expect(detectProvider('pk-abc123')).toBe('invalid');
    expect(detectProvider('')).toBe('invalid');
    expect(detectProvider('not-a-key')).toBe('invalid');
  });
});

describe('validateKeyForProvider', () => {
  it('returns ok when key matches declared provider', () => {
    expect(validateKeyForProvider('sk-ant-api03-abc', 'claude')).toEqual({ ok: true });
    expect(validateKeyForProvider('sk-proj-abc', 'openai')).toEqual({ ok: true });
  });

  it('returns error when key prefix conflicts with declared provider', () => {
    const result = validateKeyForProvider('sk-ant-api03-abc', 'openai');
    expect(result.ok).toBe(false);
    expect(result.error).toMatch(/prefix does not match/i);
  });

  it('returns error when key is invalid regardless of provider', () => {
    const result = validateKeyForProvider('not-a-key', 'claude');
    expect(result.ok).toBe(false);
  });
});
