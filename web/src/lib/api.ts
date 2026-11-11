import "server-only";

import type {
  BookDetail,
  BookSummary,
  DailyLow,
  Offer,
  SearchResult,
  Verdict,
} from "@/lib/types";

/** The backend, as the Next.js server reaches it (never the browser). */
const API_URL = process.env.API_URL ?? "http://localhost:8000";

/** Prices change once a day; a few minutes of cache costs nothing. */
const REVALIDATE_SECONDS = 300;

export const PAGE_SIZE = 20;

type Json = Record<string, unknown>;

async function get(path: string): Promise<Json | null> {
  const response = await fetch(`${API_URL}${path}`, {
    next: { revalidate: REVALIDATE_SECONDS },
    headers: { Accept: "application/vnd.api+json" },
  });
  if (response.status === 404) return null;
  if (!response.ok) {
    throw new Error(`GET ${path} answered ${response.status}`);
  }
  return (await response.json()) as Json;
}

function toSummary(attributes: Json): BookSummary {
  return {
    isbn13: attributes.isbn13 as string,
    title: attributes.title as string,
    authors: (attributes.authors as string[]) ?? [],
    coverUrl: (attributes.cover_url as string | null) ?? null,
    lowestNew: (attributes.lowest_new as number | null) ?? null,
    lowestUsed: (attributes.lowest_used as number | null) ?? null,
    offerCount: (attributes.offer_count as number) ?? 0,
  };
}

function toOffer(raw: Json): Offer {
  return {
    store: raw.store as string,
    url: raw.url as string,
    condition: raw.condition as Offer["condition"],
    price: (raw.price as number | null) ?? null,
    isAvailable: Boolean(raw.is_available),
    lastCheckedAt: (raw.last_checked_at as string | null) ?? null,
  };
}

const num = (value: unknown): number | null => (value as number | null) ?? null;

function toVerdict(raw: Json): Verdict {
  return {
    condition: raw.condition as Verdict["condition"],
    status: raw.status as Verdict["status"],
    current: num(raw.current),
    days: (raw.days as number) ?? 0,
    low: num(raw.low),
    high: num(raw.high),
    p25: num(raw.p25),
    p75: num(raw.p75),
  };
}

export async function searchBooks(query: string, page = 1): Promise<SearchResult> {
  const params = new URLSearchParams({
    q: query,
    limit: String(PAGE_SIZE),
    offset: String((Math.max(1, page) - 1) * PAGE_SIZE),
  });
  const body = await get(`/books/?${params}`);
  const data = (body?.data as Json[]) ?? [];
  return {
    books: data.map((item) => toSummary(item.attributes as Json)),
    total: ((body?.meta as Json)?.total as number) ?? 0,
  };
}

export async function getBook(isbn: string): Promise<BookDetail | null> {
  const body = await get(`/books/${encodeURIComponent(isbn)}`);
  if (!body) return null;
  const attributes = (body.data as Json).attributes as Json;
  return {
    ...toSummary(attributes),
    subtitle: (attributes.subtitle as string | null) ?? null,
    publisher: (attributes.publisher as string | null) ?? null,
    year: (attributes.year as number | null) ?? null,
    pageCount: (attributes.page_count as number | null) ?? null,
    synopsis: (attributes.synopsis as string | null) ?? null,
    offers: ((attributes.offers as Json[]) ?? []).map(toOffer),
    verdicts: ((attributes.verdicts as Json[]) ?? []).map(toVerdict),
  };
}

export async function getDailyLows(isbn: string, days = 90): Promise<DailyLow[]> {
  const body = await get(
    `/books/${encodeURIComponent(isbn)}/price-history?days=${days}`,
  );
  return ((body?.data as Json[]) ?? []).map((raw) => ({
    day: raw.day as string,
    condition: raw.condition as DailyLow["condition"],
    price: raw.price as number,
  }));
}

/** Every book in the catalog (the sitemap), fetched a page at a time. */
export async function listBooks(): Promise<BookSummary[]> {
  const books: BookSummary[] = [];
  for (let offset = 0; ; offset += 50) {
    const body = await get(`/books/index?limit=50&offset=${offset}`);
    const data = (body?.data as Json[]) ?? [];
    books.push(...data.map((item) => toSummary(item.attributes as Json)));
    const total = ((body?.meta as Json)?.total as number) ?? 0;
    if (data.length === 0 || books.length >= total) return books;
  }
}
