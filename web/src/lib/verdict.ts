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

/**
 * The price the "warn me" link suggests, in whole reais: the usual low
 * (25th percentile) once there is a verdict, 10% under today's lowest while
 * still learning. Null when there is nothing to base it on.
 */
export function suggestedAlertPrice(verdict: Verdict | undefined): number | null {
  if (!verdict) return null;
  const base =
    isJudged(verdict) && verdict.p25 != null
      ? verdict.p25
      : verdict.current != null
        ? verdict.current * 0.9
        : null;
  if (base == null) return null;
  const price = Math.floor(base);
  return price >= 1 ? price : null;
}

const LINK_CONDITION: Record<string, string> = { used: "usado", new: "novo" };

/**
 * The logged-in app's "new book alert" page (Phase 4d), or null when the app
 * address is not configured. The app asks for a login and comes back here.
 */
export function alertHref(
  appUrl: string | undefined,
  isbn13: string,
  condition: "new" | "used",
  price: number | null,
): string | null {
  if (!appUrl) return null;
  const params = new URLSearchParams({ isbn: isbn13, condicao: LINK_CONDITION[condition] });
  if (price != null) params.set("preco", String(price));
  return `${appUrl.replace(/\/+$/, "")}/alertas/novo?${params}`;
}
