/**
 * "My alerts" (Phase 5c): the shapes GET /me/alerts returns and what the
 * page says about them. Pure functions, so they are tested without a server.
 */

import { formatPrice, storeName } from "@/lib/format";
import type { VerdictStatus } from "@/lib/types";

export type AlertCondition = "new" | "used" | "any";

export interface MyAlert {
  id: string;
  condition: AlertCondition;
  maxPrice: number;
  isActive: boolean;
  createdAt: string | null;
  product: {
    id: number;
    category: string;
    title: string;
    isbn13: string | null;
    coverUrl: string | null;
  } | null;
  /** Today's cheapest offer in the alert's condition; null when none is in stock. */
  today: {
    condition: "new" | "used";
    price: number;
    store: string;
    verdict: VerdictStatus | null;
  } | null;
  notices: { total: number; recent: { sentAt: string; store: string | null }[] };
}

type Json = Record<string, unknown>;

export function toMyAlert(resource: Json): MyAlert {
  const a = resource.attributes as Json;
  const product = a.product as Json | null;
  const today = a.today as Json | null;
  const notices = (a.notices as Json | null) ?? {};
  return {
    id: String(resource.id),
    condition: ((a.condition as AlertCondition) ?? "any"),
    maxPrice: Number(a.max_price),
    isActive: Boolean(a.is_active),
    createdAt: (a.created_at as string | null) ?? null,
    product: product
      ? {
          id: product.id as number,
          category: product.category as string,
          title: product.title as string,
          isbn13: (product.isbn13 as string | null) ?? null,
          coverUrl: (product.cover_url as string | null) ?? null,
        }
      : null,
    today: today
      ? {
          condition: today.condition as "new" | "used",
          price: Number(today.price),
          store: today.store as string,
          verdict: (today.verdict as VerdictStatus | null) ?? null,
        }
      : null,
    notices: {
      total: (notices.total as number) ?? 0,
      recent: ((notices.recent as Json[]) ?? []).map((n) => ({
        sentAt: n.sent_at as string,
        store: (n.store as string | null) ?? null,
      })),
    },
  };
}

const CATEGORY: Record<string, string> = { book: "Livro" };
const CONDITION: Record<AlertCondition, string> = {
  new: "Novo",
  used: "Usado",
  any: "Novo ou usado",
};

/** "Livro · Usado": what kind of product and which copies the alert watches. */
export function alertKind(alert: MyAlert): string {
  const category = CATEGORY[alert.product?.category ?? ""] ?? "Produto";
  return `${category} · ${CONDITION[alert.condition]}`;
}

export interface TargetLine {
  text: string;
  reached: boolean;
}

/** Today's price against the target: "Hoje R$ 18,00 na Estante Virtual · faltam R$ 3,00". */
export function targetLine(alert: MyAlert): TargetLine {
  if (!alert.today) {
    return { text: `Sem oferta em estoque hoje · seu alvo ${formatPrice(alert.maxPrice)}`, reached: false };
  }
  const { price, store } = alert.today;
  const today = `Hoje ${formatPrice(price)} na ${storeName(store)}`;
  if (price <= alert.maxPrice) {
    return { text: `${today} · abaixo do seu alvo de ${formatPrice(alert.maxPrice)}!`, reached: true };
  }
  const gap = Math.round((price - alert.maxPrice) * 100) / 100;
  return {
    text: `${today} · seu alvo ${formatPrice(alert.maxPrice)} · faltam ${formatPrice(gap)}`,
    reached: false,
  };
}

/** The verdict as a small badge; null while there is nothing to say. */
export function verdictBadge(
  status: VerdictStatus | null | undefined,
): { label: string; tone: "good" | "normal" | "high" } | null {
  switch (status) {
    case "good":
      return { label: "Bom preço", tone: "good" };
    case "normal":
      return { label: "Preço normal", tone: "normal" };
    case "high":
      return { label: "Caro agora", tone: "high" };
    default:
      return null;
  }
}

const DATE = new Intl.DateTimeFormat("pt-BR", {
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "America/Sao_Paulo",
});

/** The backend sends naive UTC timestamps ("2026-11-11T14:00:00"). */
export function parseUtc(iso: string): Date {
  return new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`);
}

/** "11 de nov., 11:00 · Estante Virtual" */
export function noticeLine(notice: { sentAt: string; store: string | null }): string {
  const when = DATE.format(parseUtc(notice.sentAt));
  return notice.store ? `${when} · ${storeName(notice.store)}` : when;
}

/** "Nenhum aviso ainda" / "1 aviso enviado" / "4 avisos enviados". */
export function noticeCount(total: number): string {
  if (total === 0) return "Nenhum aviso enviado ainda";
  return total === 1 ? "1 aviso enviado" : `${total} avisos enviados`;
}

/* ── The "warn me" link: /alertas/novo?isbn=…&condicao=usado&preco=25 ── */

const CONDITION_FROM_LINK: Record<string, AlertCondition> = {
  usado: "used",
  novo: "new",
  qualquer: "any",
  used: "used",
  new: "new",
  any: "any",
};

export function conditionFromLink(raw: string | null | undefined): AlertCondition {
  return CONDITION_FROM_LINK[raw ?? ""] ?? "any";
}

/** The suggested price as the form shows it ("25,90"), or "" when missing or invalid. */
export function priceFromLink(raw: string | null | undefined): string {
  const value = Number(raw);
  return raw && Number.isFinite(value) && value > 0 ? value.toFixed(2).replace(".", ",") : "";
}

/** What the person typed ("25,90", "25.90", "R$ 25") as a number; NaN when invalid. */
export function parsePrice(text: string): number {
  const clean = text.replace(/R\$\s*/i, "").trim();
  // "1.234,56" -> "1234.56"; "25,90" -> "25.90"; "25.90" stays.
  const normal = clean.includes(",") ? clean.replace(/\./g, "").replace(",", ".") : clean;
  const value = Number(normal);
  return clean && Number.isFinite(value) && value > 0 ? Math.round(value * 100) / 100 : NaN;
}

/** The new-alert page's own address, so a sign-in comes back to it. */
export function newAlertPath(isbn: string, condition: AlertCondition, price: number | null): string {
  const link: Record<AlertCondition, string> = { used: "usado", new: "novo", any: "qualquer" };
  const params = new URLSearchParams({ isbn, condicao: link[condition] });
  if (price != null) params.set("preco", String(price));
  return `/alertas/novo?${params}`;
}
