import { describe, it, expect, vi, afterEach } from 'vitest';
import {
  validateSql,
  enforceLimitClause,
  rewriteSqlForWasm,
  extractParquetUrls,
  DataUnavailableError,
  checkParquetReachable,
} from '@/lib/scout-guards';

// ---------------------------------------------------------------------------
// validateSql
// ---------------------------------------------------------------------------

describe('validateSql', () => {
  it('allows a valid SELECT statement', () => {
    const result = validateSql('SELECT id, name FROM places LIMIT 10');
    expect(result.valid).toBe(true);
  });

  it('allows LOAD + SELECT (DuckDB-Wasm pattern)', () => {
    const result = validateSql('LOAD spatial;\nSELECT id FROM places LIMIT 10;');
    expect(result.valid).toBe(true);
  });

  const forbidden = [
    ['DROP', 'DROP TABLE places'],
    ['DELETE', 'DELETE FROM places WHERE id = 1'],
    ['INSERT', "INSERT INTO places VALUES ('x')"],
    ['UPDATE', "UPDATE places SET name = 'x'"],
    ['CREATE', 'CREATE TABLE foo AS SELECT * FROM places'],
    ['TRUNCATE', 'TRUNCATE TABLE places'],
    ['ALTER', 'ALTER TABLE places ADD COLUMN x INT'],
    ['GRANT', 'GRANT SELECT ON places TO user'],
    ['REVOKE', 'REVOKE SELECT ON places FROM user'],
    ['EXEC', 'EXEC sp_something'],
    ['EXECUTE', 'EXECUTE sp_something'],
    ['chained SELECTs', 'SELECT 1; SELECT 2'],
  ] as const;

  for (const [label, sql] of forbidden) {
    it(`blocks ${label}`, () => {
      const result = validateSql(sql);
      expect(result.valid).toBe(false);
      expect(result.reason).toMatch(/Forbidden SQL pattern/);
    });
  }
});

// ---------------------------------------------------------------------------
// enforceLimitClause
// ---------------------------------------------------------------------------

describe('enforceLimitClause', () => {
  it('appends LIMIT 500 when no LIMIT present', () => {
    const result = enforceLimitClause('SELECT id FROM places');
    expect(result).toMatch(/LIMIT 500/i);
  });

  it('clamps LIMIT to max when too high', () => {
    const result = enforceLimitClause('SELECT id FROM places LIMIT 1000');
    expect(result).toMatch(/LIMIT 500/i);
    expect(result).not.toMatch(/LIMIT 1000/i);
  });

  it('leaves LIMIT unchanged when within max', () => {
    const result = enforceLimitClause('SELECT id FROM places LIMIT 10');
    expect(result).toMatch(/LIMIT 10/i);
  });

  it('respects a custom max parameter', () => {
    const result = enforceLimitClause('SELECT id FROM places LIMIT 999', 200);
    expect(result).toMatch(/LIMIT 200/i);
  });
});

// ---------------------------------------------------------------------------
// rewriteSqlForWasm
// Note: these tests depend on SCOUT_DATASETS registry from scout-datasets.ts
// They are integration tests for the guard+registry combination.
// ---------------------------------------------------------------------------

describe('rewriteSqlForWasm', () => {
  const origin = 'http://localhost:3000';

  it('strips LOAD spatial; statement', () => {
    const sql = 'LOAD spatial;\nSELECT id FROM places LIMIT 10';
    const result = rewriteSqlForWasm(sql, origin);
    expect(result).not.toMatch(/LOAD spatial/i);
  });

  it('strips other LOAD statements (e.g. LOAD json;)', () => {
    const sql = 'LOAD json;\nSELECT id FROM places LIMIT 10';
    const result = rewriteSqlForWasm(sql, origin);
    expect(result).not.toMatch(/LOAD json/i);
  });

  it('rewrites FROM places to read_parquet with local URL', () => {
    const sql = 'SELECT id, name FROM places LIMIT 10';
    const result = rewriteSqlForWasm(sql, origin);
    expect(result).toContain(`read_parquet('${origin}/data/sf_places.parquet')`);
    expect(result).not.toContain('FROM places');
  });

  it('rewrites JOIN places to read_parquet', () => {
    const sql = 'SELECT p.id FROM other o JOIN places p ON o.id = p.id LIMIT 10';
    const result = rewriteSqlForWasm(sql, origin);
    expect(result).toContain(`JOIN read_parquet('${origin}/data/sf_places.parquet')`);
  });

  it('redirects hallucinated https:// read_parquet URLs to local URL', () => {
    const sql = `SELECT id FROM read_parquet('https://data.sfscout.org/places.parquet') LIMIT 10`;
    const result = rewriteSqlForWasm(sql, origin);
    expect(result).not.toContain('https://data.sfscout.org');
    expect(result).toContain(origin);
  });

  it('catch-all replaces any remaining external https:// read_parquet URL', () => {
    const sql = `SELECT id FROM read_parquet('https://some-random-bucket.s3.amazonaws.com/data.parquet') LIMIT 10`;
    const result = rewriteSqlForWasm(sql, origin);
    expect(result).not.toContain('https://some-random-bucket.s3.amazonaws.com');
    expect(result).toContain(origin);
  });
});

// ---------------------------------------------------------------------------
// extractParquetUrls
// ---------------------------------------------------------------------------

describe('extractParquetUrls', () => {
  const origin = 'http://localhost:3000';

  it('finds a single URL and returns correct dataset label', () => {
    const sql = `SELECT id FROM read_parquet('${origin}/data/sf_places.parquet') LIMIT 10`;
    const results = extractParquetUrls(sql);
    expect(results).toHaveLength(1);
    expect(results[0].url).toBe(`${origin}/data/sf_places.parquet`);
    // Should match the dataset label, not the raw filename
    expect(results[0].label).not.toBe('');
  });

  it('deduplicates repeated URLs', () => {
    const url = `${origin}/data/sf_places.parquet`;
    const sql = `SELECT a.id FROM read_parquet('${url}') a JOIN read_parquet('${url}') b ON a.id = b.id`;
    const results = extractParquetUrls(sql);
    expect(results).toHaveLength(1);
  });

  it('returns filename as label when no dataset match', () => {
    const sql = `SELECT id FROM read_parquet('${origin}/data/unknown_dataset.parquet') LIMIT 10`;
    const results = extractParquetUrls(sql);
    expect(results).toHaveLength(1);
    expect(results[0].label).toBe('unknown_dataset.parquet');
  });
});

// ---------------------------------------------------------------------------
// DataUnavailableError
// ---------------------------------------------------------------------------

describe('DataUnavailableError', () => {
  it('sets message, datasetLabel, and parquetUrl properties', () => {
    const err = new DataUnavailableError('data missing', 'SF Places', 'http://localhost/places.parquet');
    expect(err.message).toBe('data missing');
    expect(err.datasetLabel).toBe('SF Places');
    expect(err.parquetUrl).toBe('http://localhost/places.parquet');
    expect(err.name).toBe('DataUnavailableError');
  });
});

// ---------------------------------------------------------------------------
// checkParquetReachable
// ---------------------------------------------------------------------------

describe('checkParquetReachable', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('resolves without throwing when fetch returns 200', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 200 }));
    await expect(checkParquetReachable('http://localhost/places.parquet', 'SF Places')).resolves.toBeUndefined();
  });

  it('throws DataUnavailableError when fetch returns non-2xx', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 404 }));
    await expect(checkParquetReachable('http://localhost/places.parquet', 'SF Places')).rejects.toBeInstanceOf(DataUnavailableError);
  });
});
