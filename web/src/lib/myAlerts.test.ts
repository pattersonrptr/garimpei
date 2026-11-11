import { describe, expect, it } from "vitest";

import {
  type MyAlert,
  alertKind,
  conditionFromLink,
  newAlertPath,
  noticeCount,
  noticeLine,
  parsePrice,
  parseUtc,
  priceFromLink,
  targetLine,
  toMyAlert,
  verdictBadge,
} from "@/lib/myAlerts";

/** Intl puts a no-break space in "R$ 18,00". */
const plain = (text: string) => text.replace(/ /g, " ");

function alert(overrides: Partial<MyAlert> = {}): MyAlert {
  return {
    id: "7",
    condition: "used",
    maxPrice: 15,
    isActive: true,
    createdAt: null,
    product: { id: 1, category: "book", title: "Dom Casmurro", isbn13: "9788535914849", coverUrl: null },
    today: { condition: "used", price: 18, store: "estante_virtual", verdict: "normal" },
    notices: { total: 0, recent: [] },
    ...overrides,
  };
}

describe("toMyAlert", () => {
  it("reads the API resource", () => {
    const parsed = toMyAlert({
      type: "my_alerts",
      id: 7,
      attributes: {
        condition: "used",
        max_price: 15,
        is_active: false,
        created_at: "2026-11-11T10:00:00",
        product: { id: 1, category: "book", title: "Dom Casmurro", isbn13: "978", cover_url: "c.jpg" },
        today: { condition: "used", price: 18.5, store: "olx", verdict: "good" },
        notices: { total: 3, recent: [{ sent_at: "2026-11-10T12:00:00", store: "olx" }] },
      },
    });
    expect(parsed.id).toBe("7");
    expect(parsed.isActive).toBe(false);
    expect(parsed.product?.coverUrl).toBe("c.jpg");
    expect(parsed.today).toEqual({ condition: "used", price: 18.5, store: "olx", verdict: "good" });
    expect(parsed.notices.recent[0]).toEqual({ sentAt: "2026-11-10T12:00:00", store: "olx" });
  });

  it("keeps a missing product and today as null", () => {
    const parsed = toMyAlert({
      id: "1",
      attributes: { max_price: 10, is_active: true, product: null, today: null },
    });
    expect(parsed.product).toBeNull();
    expect(parsed.today).toBeNull();
    expect(parsed.condition).toBe("any");
    expect(parsed.notices).toEqual({ total: 0, recent: [] });
  });
});

describe("targetLine", () => {
  it("says how much is missing", () => {
    const line = targetLine(alert());
    expect(line.reached).toBe(false);
    expect(plain(line.text)).toBe(
      "Hoje R$ 18,00 na Estante Virtual · seu alvo R$ 15,00 · faltam R$ 3,00",
    );
  });

  it("celebrates a price at or under the target", () => {
    const line = targetLine(
      alert({ today: { condition: "used", price: 15, store: "olx", verdict: null } }),
    );
    expect(line.reached).toBe(true);
    expect(plain(line.text)).toBe("Hoje R$ 15,00 na OLX · abaixo do seu alvo de R$ 15,00!");
  });

  it("handles no offer in stock", () => {
    expect(plain(targetLine(alert({ today: null })).text)).toBe(
      "Sem oferta em estoque hoje · seu alvo R$ 15,00",
    );
  });

  it("rounds the gap to cents", () => {
    const line = targetLine(
      alert({ maxPrice: 10.1, today: { condition: "used", price: 10.3, store: "olx", verdict: null } }),
    );
    expect(plain(line.text)).toContain("faltam R$ 0,20");
  });
});

describe("labels", () => {
  it("names the product kind and condition", () => {
    expect(alertKind(alert())).toBe("Livro · Usado");
    expect(alertKind(alert({ condition: "any" }))).toBe("Livro · Novo ou usado");
    expect(alertKind(alert({ product: null }))).toBe("Produto · Usado");
  });

  it("shows a badge only for a judged price", () => {
    expect(verdictBadge("good")).toEqual({ label: "Bom preço", tone: "good" });
    expect(verdictBadge("high")?.tone).toBe("high");
    expect(verdictBadge("learning")).toBeNull();
    expect(verdictBadge(null)).toBeNull();
  });

  it("counts notices", () => {
    expect(noticeCount(0)).toBe("Nenhum aviso enviado ainda");
    expect(noticeCount(1)).toBe("1 aviso enviado");
    expect(noticeCount(4)).toBe("4 avisos enviados");
  });

  it("reads naive timestamps as UTC and shows Brazil's time", () => {
    expect(parseUtc("2026-11-11T14:00:00").toISOString()).toBe("2026-11-11T14:00:00.000Z");
    expect(parseUtc("2026-11-11T14:00:00+00:00").toISOString()).toBe("2026-11-11T14:00:00.000Z");
    const line = noticeLine({ sentAt: "2026-11-11T14:00:00", store: "estante_virtual" });
    expect(line).toContain("11:00");
    expect(line).toContain("Estante Virtual");
  });
});

describe("the warn-me link", () => {
  it("reads the condition, Portuguese or not", () => {
    expect(conditionFromLink("usado")).toBe("used");
    expect(conditionFromLink("novo")).toBe("new");
    expect(conditionFromLink("new")).toBe("new");
    expect(conditionFromLink(undefined)).toBe("any");
    expect(conditionFromLink("x")).toBe("any");
  });

  it("shows the suggested price the Brazilian way", () => {
    expect(priceFromLink("25")).toBe("25,00");
    expect(priceFromLink("25.9")).toBe("25,90");
    expect(priceFromLink("-1")).toBe("");
    expect(priceFromLink("abc")).toBe("");
    expect(priceFromLink(undefined)).toBe("");
  });

  it("parses what people type", () => {
    expect(parsePrice("25,90")).toBe(25.9);
    expect(parsePrice("25.90")).toBe(25.9);
    expect(parsePrice("R$ 1.234,56")).toBe(1234.56);
    expect(parsePrice(" 30 ")).toBe(30);
    expect(parsePrice("0")).toBeNaN();
    expect(parsePrice("")).toBeNaN();
    expect(parsePrice("vinte")).toBeNaN();
  });

  it("builds the page address", () => {
    expect(newAlertPath("978", "any", null)).toBe("/alertas/novo?isbn=978&condicao=qualquer");
    expect(newAlertPath("978", "used", 25.9)).toBe(
      "/alertas/novo?isbn=978&condicao=usado&preco=25.9",
    );
  });
});
