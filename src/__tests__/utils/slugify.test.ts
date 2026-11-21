import { describe, it, expect } from 'vitest';
import { slugify } from '@/utils/slugify';

describe('slugify', () => {
  it('lowercases text', () => {
    expect(slugify('Overview')).toBe('overview');
  });

  it('replaces spaces with hyphens', () => {
    expect(slugify('Key Concepts')).toBe('key-concepts');
  });

  it('strips special characters', () => {
    expect(slugify('What is COG?')).toBe('what-is-cog');
  });

  it('collapses multiple spaces', () => {
    expect(slugify('Cloud  Storage')).toBe('cloud-storage');
  });

  it('trims leading/trailing whitespace', () => {
    expect(slugify('  Overview  ')).toBe('overview');
  });

  it('handles numbers', () => {
    expect(slugify('1. Introduction')).toBe('1-introduction');
  });

  it('handles hyphens already present', () => {
    expect(slugify('Cloud-Native Formats')).toBe('cloud-native-formats');
  });
});
