import { describe, expect, it } from "vitest";

import type { Verdict } from "@/lib/types";
import {
  barPosition,
  headlineVerdict,
  secondaryVerdict,
  verdictShort,
  verdictText,
} from "@/lib/verdict";

function verdict(overrides: Partial<Verdict>): Verdict {
  return {
    condition: "used",
    status: "good",
    current: 30,
    days: 20,
    low: 30,
    high: 49,
    p25: 34.75,
    p75: 44.25,
    ...overrides,
  };
}

/** Intl puts a no-break space after "R$". */
const plain = (text: string) => text.replace(/ /g, " ");

describe("headlineVerdict", () => {
  it("leads with used", () => {
    const used = verdict({});
    expect(headlineVerdict([verdict({ condition: "new" }), used])).toBe(used);
  });

  it("falls back to new when no used copy is in stock", () => {
    const fresh = verdict({ condition: "new" });
    expect(headlineVerdict([verdict({ status: "no_offer" }), fresh])).toBe(fresh);
  });

  it("is null when nothing is in stock", () => {
    expect(headlineVerdict([verdict({ status: "no_offer" })])).toBeNull();
    expect(headlineVerdict([])).toBeNull();
  });
});

describe("secondaryVerdict", () => {
  it("is the other condition, only when judged", () => {
    const used = verdict({});
    const fresh = verdict({ condition: "new", status: "high" });
    expect(secondaryVerdict([used, fresh], used)).toBe(fresh);
    const learning = verdict({ condition: "new", status: "learning" });
    expect(secondaryVerdict([used, learning], used)).toBeNull();
  });
});

describe("verdictText", () => {
  it("says good, normal and high in Portuguese", () => {
    expect(verdictText(verdict({})).title).toBe("Bom preço");
    const normal = verdictText(verdict({ status: "normal", current: 40 }));
    expect(plain(normal.detail)).toContain("R$ 34,75 a R$ 44,25");
    const high = verdictText(verdict({ status: "high", current: 49 }));
    expect(high.title).toBe("Caro agora: vale esperar");
    expect(plain(high.detail)).toContain("já saiu por R$ 30,00");
  });

  it("never guesses while learning", () => {
    const text = verdictText(verdict({ status: "learning", days: 1 }));
    expect(text.title).toBe("Ainda aprendendo o preço deste livro");
    expect(text.detail).toBe("Temos 1 dia de histórico. O veredito aparece com 14 dias.");
  });

  it("has a short form", () => {
    const fresh = verdict({ condition: "new", status: "normal", current: 80 });
    expect(plain(verdictShort(fresh))).toBe("Novo por R$ 80,00: preço normal");
  });
});

describe("barPosition", () => {
  it("places the price between the low and the high", () => {
    expect(barPosition(verdict({ current: 30 }))).toBe(0);
    expect(barPosition(verdict({ current: 49 }))).toBe(1);
    expect(barPosition(verdict({ current: 39.5 }))).toBeCloseTo(0.5);
  });

  it("clamps prices outside the range", () => {
    expect(barPosition(verdict({ current: 20 }))).toBe(0);
    expect(barPosition(verdict({ current: 60 }))).toBe(1);
  });

  it("draws no bar when every day had the same price", () => {
    expect(barPosition(verdict({ low: 30, high: 30 }))).toBeNull();
  });

  it("is null without a price or history", () => {
    expect(barPosition(verdict({ current: null }))).toBeNull();
    expect(barPosition(verdict({ low: null, high: null }))).toBeNull();
  });
});
