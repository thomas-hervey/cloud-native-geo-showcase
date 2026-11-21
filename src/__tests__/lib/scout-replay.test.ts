import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import indexJson from '@/content/scout-replays/index.json';
import { ReplayIndexSchema, ScoutReplaySchema, describeReplay } from '@/lib/scout-replay';

const REPLAY_DIR = path.join(process.cwd(), 'src', 'content', 'scout-replays');

function fixtureFiles(): string[] {
  return fs.readdirSync(REPLAY_DIR).filter((f) => f.endsWith('.json') && f !== 'index.json');
}

describe('scout replay index', () => {
  it('validates index.json against the schema', () => {
    expect(() => ReplayIndexSchema.parse(indexJson)).not.toThrow();
  });

  it('lists exactly the fixture files that exist on disk', () => {
    const ids = ReplayIndexSchema.parse(indexJson).map((e) => e.id).sort();
    const files = fixtureFiles().map((f) => f.replace(/\.json$/, '')).sort();
    expect(ids).toEqual(files);
  });

  it('rejects duplicate ids', () => {
    const dupes = [
      { id: 'a', title: 'A', query: 'q' },
      { id: 'a', title: 'A again', query: 'q' },
    ];
    expect(ReplayIndexSchema.safeParse(dupes).success).toBe(false);
  });

  it('rejects ids that are not safe path segments', () => {
    for (const id of ['../secrets', 'a/b', 'UPPER', '']) {
      expect(ReplayIndexSchema.safeParse([{ id, title: 'x', query: 'x' }]).success).toBe(false);
    }
  });
});

describe('scout replay fixtures', () => {
  it.each(fixtureFiles())('%s validates against ScoutReplaySchema', (file) => {
    const raw = JSON.parse(fs.readFileSync(path.join(REPLAY_DIR, file), 'utf-8'));
    const result = ScoutReplaySchema.safeParse(raw);
    expect(result.success).toBe(true);
    expect(raw.id).toBe(file.replace(/\.json$/, ''));
  });

  it('marks placeholder fixtures with a [sample] title and null recordedAt', () => {
    for (const file of fixtureFiles()) {
      const replay = ScoutReplaySchema.parse(JSON.parse(fs.readFileSync(path.join(REPLAY_DIR, file), 'utf-8')));
      if (replay.recordedAt === null) {
        expect(replay.title.startsWith('[sample]')).toBe(true);
      }
    }
  });

  it('rejects a fixture with a malformed recordedAt', () => {
    const bad = {
      id: 'x', title: 'x', query: 'x', sql: 'SELECT 1', narrative: '', count: 0,
      features: [], model: 'm', recordedAt: 'yesterday', approxCostUsd: 0,
    };
    expect(ScoutReplaySchema.safeParse(bad).success).toBe(false);
  });
});

describe('describeReplay', () => {
  it('labels placeholders as not a real recording', () => {
    expect(describeReplay({ model: 'm', recordedAt: null })).toMatch(/not a real recording/);
  });

  it('labels real recordings with model and date', () => {
    expect(describeReplay({ model: 'claude-sonnet-4-6', recordedAt: '2026-11-01T12:00:00.000Z' }))
      .toBe('Recorded run · claude-sonnet-4-6 · 2026-11-01');
  });
});
