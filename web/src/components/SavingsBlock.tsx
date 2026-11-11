import { formatPrice, savingsPercent } from "@/lib/format";

/**
 * The used highlight (Phase 0): how much less the cheapest used copy costs
 * than the cheapest new one. Disappears when there is no used copy in stock.
 */
export function SavingsBlock({
  lowestUsed,
  lowestNew,
}: {
  lowestUsed: number | null;
  lowestNew: number | null;
}) {
  if (lowestUsed == null) return null;
  const percent = savingsPercent(lowestUsed, lowestNew);
  return (
    <section className="savings" aria-label="Economia com usado">
      <p className="savings-main">
        Usado a partir de <strong className="price used">{formatPrice(lowestUsed)}</strong>
      </p>
      {percent != null ? (
        <p>
          <strong className="good">{percent}% menos</strong> que o novo mais barato (
          {formatPrice(lowestNew)}).
        </p>
      ) : (
        lowestNew != null && (
          <p className="muted">
            Hoje o novo está igual ou mais barato ({formatPrice(lowestNew)}).
          </p>
        )
      )}
    </section>
  );
}
