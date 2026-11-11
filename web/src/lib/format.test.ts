import { describe, expect, it } from "vitest";

import {
  bookPath,
  formatPrice,
  isbnFromSegment,
  savingsPercent,
  slugify,
  storeName,
  updatedAgo,
} from "@/lib/format";

describe("formatPrice", () => {
  it("formats reais", () => {
    expect(formatPrice(49.9).replace(/\s/g, " ")).toBe("R$ 49,90");
  });
  it("shows a dash when there is no price", () => {
    expect(formatPrice(null)).toBe("—");
  });
});

describe("updatedAgo", () => {
  const now = new Date("2026-11-10T15:00:00Z");
  it("says recent prices are fresh", () => {
    expect(updatedAgo("2026-11-10T14:30:00Z", now)).toBe("agora há pouco");
  });
  it("counts hours", () => {
    expect(updatedAgo("2026-11-10T12:00:00+00:00", now)).toBe("há 3 h");
  });
  it("counts days", () => {
    expect(updatedAgo("2026-11-09T14:00:00Z", now)).toBe("há 1 dia");
    expect(updatedAgo("2026-11-05T15:00:00Z", now)).toBe("há 5 dias");
  });
  it("handles offers never checked", () => {
    expect(updatedAgo(null, now)).toBe("ainda não verificado");
  });
});

describe("storeName", () => {
  it("knows the stores", () => {
    expect(storeName("estante_virtual")).toBe("Estante Virtual");
  });
  it("makes a readable name for a new store", () => {
    expect(storeName("livraria_cultura")).toBe("Livraria Cultura");
  });
});

describe("book addresses", () => {
  it("slugifies titles without accents", () => {
    expect(slugify("Cem anos de solidão!")).toBe("cem-anos-de-solidao");
  });
  it("puts the ISBN first and reads it back", () => {
    const path = bookPath("9788501012074", "Cem anos de solidão");
    expect(path).toBe("/livro/9788501012074-cem-anos-de-solidao");
    expect(isbnFromSegment(path.split("/")[2])).toBe("9788501012074");
  });
});

describe("savingsPercent", () => {
  it("is how much cheaper used is than new", () => {
    expect(savingsPercent(28.5, 54.9)).toBe(48);
  });
  it("is null when used is not cheaper or a price is missing", () => {
    expect(savingsPercent(60, 54.9)).toBeNull();
    expect(savingsPercent(null, 54.9)).toBeNull();
    expect(savingsPercent(20, null)).toBeNull();
  });
});
