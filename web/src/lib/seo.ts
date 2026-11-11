/** What search engines read: absolute URLs and schema.org data. */

import type { BookDetail } from "@/lib/types";

/** The public address of the site (for the sitemap and structured data). */
export function siteUrl(): string {
  return (process.env.SITE_URL ?? "http://localhost:3000").replace(/\/+$/, "");
}

/**
 * schema.org Book with an AggregateOffer over the offers in stock: lets a
 * search result show "from R$ X". Only prices and links, as the stores show.
 */
export function bookJsonLd(book: BookDetail, path: string, base: string = siteUrl()) {
  const inStock = book.offers.filter((o) => o.isAvailable && o.price != null);
  const prices = inStock.map((o) => o.price as number);
  return {
    "@context": "https://schema.org",
    "@type": "Book",
    name: book.title,
    isbn: book.isbn13,
    url: `${base}${path}`,
    ...(book.authors.length && {
      author: book.authors.map((name) => ({ "@type": "Person", name })),
    }),
    ...(book.publisher && { publisher: { "@type": "Organization", name: book.publisher } }),
    ...(book.coverUrl && { image: book.coverUrl }),
    ...(prices.length && {
      offers: {
        "@type": "AggregateOffer",
        priceCurrency: "BRL",
        lowPrice: Math.min(...prices),
        highPrice: Math.max(...prices),
        offerCount: prices.length,
      },
    }),
  };
}
