import { describe, it, expect } from 'vitest';
import storyJson from '@/content/spatial-eval/story-findings.json';
import { describeOffset, placeAgreementRows, storyFindingsSchema } from '@/lib/spatial-eval-story';

describe('spatial-eval story findings', () => {
  const findings = storyFindingsSchema.parse(storyJson);

  it('should match the exported JSON contract', () => {
    expect(findings.answers.n).toBeGreaterThan(0);
    expect(findings.places.length).toBeGreaterThan(0);
  });

  it('should only attach reference agreement to places with all three source pairs', () => {
    const rows = placeAgreementRows(findings);
    const panhandle = rows.find((r) => r.place === 'The Panhandle');
    expect(panhandle?.referenceLowestIou).toBeNull();
    expect(rows.find((r) => r.place === 'The Mission')?.referenceLowestIou).not.toBeNull();
  });

  it('should describe signed offsets in plain words', () => {
    expect(describeOffset(-1436, -358)).toBe('1.4 km west, 0.4 km south');
    expect(describeOffset(200, 1500)).toBe('0.2 km east, 1.5 km north');
  });
});
