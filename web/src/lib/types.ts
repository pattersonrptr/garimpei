/** Shapes the public book API (/books) returns, as the pages use them. */

export type Condition = "new" | "used" | "refurbished" | "undetermined";

export interface BookSummary {
  isbn13: string;
  title: string;
  authors: string[];
  coverUrl: string | null;
  lowestNew: number | null;
  lowestUsed: number | null;
  offerCount: number;
}

export interface Offer {
  store: string;
  url: string;
  condition: Condition;
  price: number | null;
  isAvailable: boolean;
  lastCheckedAt: string | null;
}

export interface BookDetail extends BookSummary {
  subtitle: string | null;
  publisher: string | null;
  year: number | null;
  pageCount: number | null;
  synopsis: string | null;
  offers: Offer[];
}

export interface DailyLow {
  day: string; // YYYY-MM-DD, Brazil's day
  condition: Condition;
  price: number;
}

export interface SearchResult {
  books: BookSummary[];
  total: number;
}
