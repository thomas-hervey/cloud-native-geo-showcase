import {
  describeOffset,
  placeAgreementRows,
  type StoryFindings as Findings,
} from '@/lib/spatial-eval-story';

const pct = (share: number) => `${Math.round(share * 100)}%`;

function Finding({
  number,
  title,
  children,
}: {
  number: number;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <article className="border-t border-gray-100 pt-5 first:border-t-0 first:pt-0">
      <h3 className="text-base font-semibold text-gray-900">
        <span className="mr-2 text-blue-600">{number}.</span>
        {title}
      </h3>
      <div className="mt-1 space-y-2 text-sm leading-relaxed text-gray-600">
        {children}
      </div>
    </article>
  );
}

function AgreementChart({ findings }: { findings: Findings }) {
  const rows = placeAgreementRows(findings);
  return (
    <figure className="mt-3 rounded-xl bg-gray-50 p-4">
      <figcaption className="mb-3 text-xs text-gray-500">
        Model accuracy by place (median IoU against SF Planning; longer bar is
        better), with how closely the reference sources agree on that place
        (lowest overlap between any two of SF Planning, Click That Hood and
        Zillow).
      </figcaption>
      <ol className="space-y-1.5">
        {rows.map((row) => (
          <li
            key={row.place}
            className="grid grid-cols-[8.5rem_1fr_6rem] items-center gap-3 text-xs"
          >
            <span className="truncate text-gray-700">{row.place}</span>
            <span
              className="h-2.5 rounded-full bg-gray-200"
              role="img"
              aria-label={`${row.place}: model IoU ${row.medianIou.toFixed(2)}`}
            >
              <span
                className="block h-full rounded-full bg-blue-600"
                style={{ width: `${Math.max(row.medianIou, 0.02) * 100}%` }}
              />
            </span>
            <span className="tabular-nums text-gray-500">
              {row.medianIou.toFixed(2)}
              {row.referenceLowestIou !== null && (
                <span className="text-gray-400">
                  {' '}
                  · refs ≥ {row.referenceLowestIou.toFixed(2)}
                </span>
              )}
            </span>
          </li>
        ))}
      </ol>
    </figure>
  );
}

export function StoryFindings({ findings }: { findings: Findings }) {
  const {
    answers,
    size,
    displaced,
    confidence,
    repeatability,
    referenceAgreement,
    noOfficialPolygon,
  } = findings;
  const high = confidence.levels.high;
  const medium = confidence.levels.medium;

  return (
    <section className="mx-auto w-full max-w-4xl rounded-2xl border border-gray-200 bg-white p-6 shadow-sm sm:p-8">
      <h2 className="text-lg font-semibold text-gray-900">
        What the data says
      </h2>
      <p className="mt-1 mb-6 text-sm leading-relaxed text-gray-500">
        {answers.n} scored answers from 5 models across 22 San Francisco
        neighborhoods. A typical answer overlaps the official boundary at an IoU
        of {answers.medianIou.toFixed(2)}, and only{' '}
        {pct(answers.shareAtLeast05)} reach 0.5.
      </p>

      <div className="space-y-5">
        <Finding
          number={1}
          title="Models know a place best where people already agree on it"
        >
          <p>
            Across {referenceAgreement.correlationPlaces} places, how well a
            model does tracks how well the human reference sources agree with
            each other (rank correlation{' '}
            {referenceAgreement.rankCorrelation.toFixed(2)}). The Mission is
            drawn almost identically by all three sources and is where models do
            best. The Sunset and the Richmond are among the places where the
            sources diverge, and where models do worst.
          </p>
          <p>
            Fame is not the same as agreement: Chinatown is a tier 1 place and
            scores below Bayview, a tier 3 one.
          </p>
          <AgreementChart findings={findings} />
        </Finding>

        <Finding number={2} title="Confident, and no more right for it">
          <p>
            In {confidence.n} stored responses from the March baseline, models
            called {pct(high.share)} of their answers “high” confidence and none
            “low”. High-confidence answers scored a median IoU of{' '}
            {high.medianIou.toFixed(2)}; “medium” ones scored{' '}
            {medium.medianIou.toFixed(2)}. The model’s own confidence says
            little about whether to trust the box.
          </p>
        </Finding>

        <Finding number={3} title="Too big, and in the wrong place">
          <p>
            {pct(size.shareLargerThanOfficial)} of answers were larger than the
            official polygon (median {size.medianAreaRatio.toFixed(1)}×).
            {displaced.map((d) => (
              <span key={d.place}>
                {' '}
                For {d.place}, the typical answer was{' '}
                {d.medianAreaRatio.toFixed(1)}× the official area, centered{' '}
                {describeOffset(d.medianEastM, d.medianNorthM)} of it.
              </span>
            ))}
          </p>
        </Finding>

        <Finding number={4} title="Stable enough to trust the comparison">
          <p>
            Asking the same model about the same place three times changes the
            IoU by a median of {repeatability.medianRange.toFixed(2)}, and by
            more than 0.2 in only {pct(repeatability.shareOver02)} of{' '}
            {repeatability.cells} cases. Gaps between models smaller than about{' '}
            {repeatability.medianRange.toFixed(2)} are noise. In the November
            re-run no model moved by more than 0.09, the two small models stayed
            at the bottom, and the top three finished within 0.04 of each other
            (table below).
          </p>
        </Finding>

        <Finding number={5} title="Places the city does not draw">
          <p>
            {noOfficialPolygon.join(' and ')} have no SF Planning polygon, so
            every model answered and there was nothing official to score
            against. For products, that is the case for supplying a polygon
            instead of trusting the model: where there is no agreed boundary,
            the model’s confident box is a guess.
          </p>
        </Finding>
      </div>
    </section>
  );
}
