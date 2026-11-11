import { formatPrice } from "@/lib/format";
import type { Verdict } from "@/lib/types";

/** Days of history the backend needs before it judges a price. */
export const MIN_DAYS = 14;

const JUDGED = new Set(["good", "normal", "high"]);

const LABEL: Record<string, string> = { used: "Usado", new: "Novo" };

/**
 * The verdict the page leads with: used first (the differentiator), new when
 * there is no used copy in stock. Null when nothing is in stock.
 */
export function headlineVerdict(verdicts: Verdict[]): Verdict | null {
  for (const condition of ["used", "new"]) {
    const verdict = verdicts.find((v) => v.condition === condition);
    if (verdict && verdict.status !== "no_offer") return verdict;
  }
  return null;
}

/** The other condition's verdict, shown as one line, only when it is judged. */
export function secondaryVerdict(
  verdicts: Verdict[],
  headline: Verdict | null,
): Verdict | null {
  if (!headline) return null;
  return (
    verdicts.find((v) => v.condition !== headline.condition && isJudged(v)) ?? null
  );
}

export function isJudged(verdict: Verdict): boolean {
  return JUDGED.has(verdict.status);
}

export interface VerdictText {
  title: string;
  detail: string;
}

/** What the verdict block says, in Portuguese. */
export function verdictText(verdict: Verdict): VerdictText {
  const what = `${LABEL[verdict.condition] ?? "Livro"} por ${formatPrice(verdict.current)}`;
  switch (verdict.status) {
    case "good":
      return {
        title: "Bom preço",
        detail: `${what}: entre os menores dos últimos 90 dias.`,
      };
    case "normal":
      return {
        title: "Preço normal",
        detail: `${what}: dentro do usual dos últimos 90 dias (${formatPrice(
          verdict.p25,
        )} a ${formatPrice(verdict.p75)}).`,
      };
    case "high":
      return {
        title: "Caro agora: vale esperar",
        detail: `${what}: acima do usual. Nos últimos 90 dias já saiu por ${formatPrice(
          verdict.low,
        )}.`,
      };
    default: {
      const days = verdict.days === 1 ? "1 dia" : `${verdict.days} dias`;
      return {
        title: "Ainda aprendendo o preço deste livro",
        detail: `Temos ${days} de histórico. O veredito aparece com ${MIN_DAYS} dias.`,
      };
    }
  }
}

/** Short form for the secondary line: "Novo por R$ 80,00: preço normal". */
export function verdictShort(verdict: Verdict): string {
  const title = verdictText(verdict).title.toLowerCase();
  return `${LABEL[verdict.condition] ?? "Livro"} por ${formatPrice(verdict.current)}: ${title}`;
}

/**
 * Where today's price sits between the 90-day low (0) and high (1).
 * Null when there is nothing to place: no price, no history, or every day had
 * the same price (a bar would say nothing).
 */
export function barPosition(verdict: Verdict): number | null {
  const { current, low, high } = verdict;
  if (current == null || low == null || high == null) return null;
  if (high <= low) return null;
  return Math.min(1, Math.max(0, (current - low) / (high - low)));
}
