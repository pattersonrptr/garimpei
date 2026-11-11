import { describe, expect, it } from "vitest";

import { bookJsonLd } from "@/lib/seo";
import type { BookDetail } from "@/lib/types";

const BOOK: BookDetail = {
  isbn13: "9788501012074",
  title: "Cem anos de solidão",
  authors: ["Gabriel García Márquez"],
  coverUrl: null,
  lowestNew: 49.9,
  lowestUsed: 30,
  offerCount: 3,
  subtitle: null,
  publisher: "Record",
  year: 1977,
  pageCount: 448,
  synopsis: null,
  offers: [
    { store: "estante_virtual", url: "u1", condition: "used", price: 30, isAvailable: true, lastCheckedAt: null },
    { store: "livraria_da_vila", url: "u2", condition: "new", price: 49.9, isAvailable: true, lastCheckedAt: null },
    { store: "martins_fontes", url: "u3", condition: "new", price: 20, isAvailable: false, lastCheckedAt: null },
  ],
};

describe("bookJsonLd", () => {
  const data = bookJsonLd(BOOK, "/livro/9788501012074-cem-anos-de-solidao", "https://garimpei.com");

  it("describes the book", () => {
    expect(data["@type"]).toBe("Book");
    expect(data.isbn).toBe("9788501012074");
    expect(data.url).toBe("https://garimpei.com/livro/9788501012074-cem-anos-de-solidao");
    expect(data.author).toEqual([{ "@type": "Person", name: "Gabriel García Márquez" }]);
  });

  it("aggregates only the offers in stock", () => {
    expect(data.offers).toEqual({
      "@type": "AggregateOffer",
      priceCurrency: "BRL",
      lowPrice: 30,
      highPrice: 49.9,
      offerCount: 2,
    });
  });

  it("leaves out offers when nothing is in stock", () => {
    const none = bookJsonLd({ ...BOOK, offers: [] }, "/x", "https://g");
    expect("offers" in none).toBe(false);
  });
});
