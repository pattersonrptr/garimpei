import { describe, expect, it } from "vitest";

import type { Verdict } from "@/lib/types";
import {
  alertHref,
  barPosition,
  headlineVerdict,
  secondaryVerdict,
  suggestedAlertPrice,
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

describe("suggestedAlertPrice", () => {
  it("is the usual low once judged, in whole reais", () => {
    expect(suggestedAlertPrice(verdict({ status: "normal", current: 40 }))).toBe(34);
  });

  it("is 10% under today's lowest while learning", () => {
    expect(suggestedAlertPrice(verdict({ status: "learning", current: 23, p25: 23 }))).toBe(20);
  });

  it("is null with nothing to base it on", () => {
    expect(suggestedAlertPrice(undefined)).toBeNull();
    expect(
      suggestedAlertPrice(verdict({ status: "no_offer", current: null, p25: null })),
    ).toBeNull();
    expect(suggestedAlertPrice(verdict({ status: "learning", current: 0.5 }))).toBeNull();
  });
});

describe("alertHref", () => {
  it("links to the app's new book alert page", () => {
    expect(alertHref("http://localhost/", "9788535914849", "used", 20)).toBe(
      "http://localhost/alertas/novo?isbn=9788535914849&condicao=usado&preco=20",
    );
  });

  it("leaves the price out when there is none", () => {
    expect(alertHref("https://app", "9788535914849", "new", null)).toBe(
      "https://app/alertas/novo?isbn=9788535914849&condicao=novo",
    );
  });

  it("is null without the app address", () => {
    expect(alertHref(undefined, "9788535914849", "used", 20)).toBeNull();
  });
});
