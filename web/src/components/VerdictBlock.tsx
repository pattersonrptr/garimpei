import { formatPrice } from "@/lib/format";
import type { Verdict } from "@/lib/types";
import {
  barPosition,
  headlineVerdict,
  isJudged,
  secondaryVerdict,
  verdictShort,
  verdictText,
} from "@/lib/verdict";

/**
 * The answer the book page opens with (Phase 0): good price, normal or wait,
 * and where today's price sits in the last 90 days. While there is too little
 * history it says so and draws no bar: never a guess.
 */
export function VerdictBlock({ verdicts }: { verdicts: Verdict[] }) {
  const headline = headlineVerdict(verdicts);
  if (!headline) return null;
  const { title, detail } = verdictText(headline);
  const other = secondaryVerdict(verdicts, headline);
  const judged = isJudged(headline);

  return (
    <section
      className={`verdict ${judged ? headline.status : "learning"}`}
      aria-label="Veredito de preço"
    >
      <p className="verdict-title">{title}</p>
      <p>{detail}</p>
      {judged && <PriceRangeBar verdict={headline} />}
      {other && <p className="verdict-other">{verdictShort(other)}</p>}
    </section>
  );
}

/** Lowest (green) to highest (red) of the last 90 days, marker at today's price. */
export function PriceRangeBar({ verdict }: { verdict: Verdict }) {
  const position = barPosition(verdict);
  if (position == null) return null;
  return (
    <div>
      <div
        className="range-bar"
        role="img"
        aria-label={`Preço de hoje, ${formatPrice(verdict.current)}, entre ${formatPrice(
          verdict.low,
        )} e ${formatPrice(verdict.high)} nos últimos 90 dias`}
      >
        <span className="range-marker" style={{ left: `${position * 100}%` }} />
      </div>
      <div className="range-labels" aria-hidden="true">
        <span>menor: {formatPrice(verdict.low)}</span>
        <span>maior: {formatPrice(verdict.high)}</span>
      </div>
    </div>
  );
}
