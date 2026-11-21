import { z } from 'zod';

/**
 * Typed contract for src/content/spatial-eval/story-findings.json, produced by
 * src/exercises/spatial-eval/scripts/export_story_findings.py.
 */
const placeSchema = z.object({
  place: z.string(),
  tier: z.number().int().nullable(),
  n: z.number().int(),
  medianIou: z.number(),
  medianCentroidErrM: z.number(),
});

const confidenceLevelSchema = z.object({
  n: z.number().int(),
  share: z.number(),
  medianIou: z.number(),
});

export const storyFindingsSchema = z.object({
  generatedAt: z.string(),
  referenceSource: z.string(),
  answers: z.object({
    n: z.number().int(),
    medianIou: z.number(),
    shareAtLeast05: z.number(),
  }),
  places: z.array(placeSchema),
  noOfficialPolygon: z.array(z.string()),
  size: z.object({
    n: z.number().int(),
    medianAreaRatio: z.number(),
    shareLargerThanOfficial: z.number(),
  }),
  displaced: z.array(
    z.object({
      place: z.string(),
      n: z.number().int(),
      medianEastM: z.number(),
      medianNorthM: z.number(),
      medianAreaRatio: z.number(),
    }),
  ),
  confidence: z.object({
    n: z.number().int(),
    levels: z.object({
      high: confidenceLevelSchema,
      medium: confidenceLevelSchema,
    }),
  }),
  repeatability: z.object({
    cells: z.number().int(),
    medianRange: z.number(),
    shareOver02: z.number(),
  }),
  referenceAgreement: z.object({
    sources: z.array(z.string()),
    places: z.array(
      z.object({
        place: z.string(),
        n: z.number().int(),
        lowestIou: z.number(),
        highestIou: z.number(),
      }),
    ),
    rankCorrelation: z.number(),
    correlationPlaces: z.number().int(),
  }),
});

export type StoryFindings = z.infer<typeof storyFindingsSchema>;

export interface PlaceAgreementRow {
  place: string;
  medianIou: number;
  /** Lowest IoU between any two human reference sources, or null when fewer than 3 pairs exist. */
  referenceLowestIou: number | null;
}

/** Joins model accuracy per place with how well the human reference sources agree there. */
export function placeAgreementRows(
  findings: StoryFindings,
): PlaceAgreementRow[] {
  const ref = new Map(
    findings.referenceAgreement.places.map((p) => [p.place, p]),
  );
  return findings.places.map((p) => {
    const r = ref.get(p.place);
    return {
      place: p.place,
      medianIou: p.medianIou,
      referenceLowestIou: r && r.n >= 3 ? r.lowestIou : null,
    };
  });
}

/** "1.4 km west, 0.4 km south" from signed east/north offsets in metres. */
export function describeOffset(eastM: number, northM: number): string {
  const part = (m: number, pos: string, neg: string) =>
    `${(Math.abs(m) / 1000).toFixed(1)} km ${m >= 0 ? pos : neg}`;
  return `${part(eastM, 'east', 'west')}, ${part(northM, 'north', 'south')}`;
}
