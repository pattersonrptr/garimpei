import { describe, expect, it } from "vitest";

import { daysBetween, priceChart, shortDate, todayInBrazil } from "@/lib/chart";
import type { DailyLow } from "@/lib/types";

const BOX = { width: 400, height: 200, left: 40, right: 10, top: 10, bottom: 30 };

const LOWS: DailyLow[] = [
  { day: "2026-11-09", condition: "new", price: 49.9 },
  { day: "2026-11-09", condition: "used", price: 30 },
  { day: "2026-11-10", condition: "used", price: 28 },
  { day: "2026-11-10", condition: "new", price: 49.9 },
  { day: "2026-07-01", condition: "used", price: 10 }, // outside the 90 days
];

describe("priceChart", () => {
  const chart = priceChart(LOWS, BOX, "2026-11-10", 90);

  it("has one series per condition, days in order, window only", () => {
    expect(chart.series.map((s) => s.condition)).toEqual(["new", "used"]);
    const used = chart.series[1];
    expect(used.points.map((p) => p.day)).toEqual(["2026-11-09", "2026-11-10"]);
  });

  it("puts today at the right edge and spans the whole window", () => {
    const used = chart.series[1];
    expect(used.points[1].x).toBeCloseTo(BOX.width - BOX.right);
    expect(chart.xLabels[0].x).toBe(BOX.left);
    expect(chart.xLabels[0].day).toBe("2026-08-13");
  });

  it("draws cheaper prices lower", () => {
    const [newSeries, used] = chart.series;
    expect(used.points[1].y).toBeGreaterThan(newSeries.points[1].y);
    expect(used.path).toMatch(/^M\d+\.\d \d+\.\d L/);
  });

  it("has round price ticks covering every price", () => {
    const prices = chart.yTicks.map((t) => t.price);
    expect(prices[0]).toBeLessThanOrEqual(28);
    expect(prices[prices.length - 1]).toBeGreaterThanOrEqual(49.9);
    expect(prices.every((p) => Number.isInteger(p / 5))).toBe(true);
  });

  it("knows when the history starts", () => {
    expect(chart.firstDay).toBe("2026-11-09");
  });

  it("handles a single price", () => {
    const one = priceChart([LOWS[0]], BOX, "2026-11-10");
    expect(one.series[0].points).toHaveLength(1);
    expect(Number.isFinite(one.series[0].points[0].y)).toBe(true);
  });

  it("handles no history", () => {
    const none = priceChart([], BOX, "2026-11-10");
    expect(none.series).toEqual([]);
    expect(none.firstDay).toBeNull();
  });
});

describe("dates", () => {
  it("formats short dates in Portuguese", () => {
    expect(shortDate("2026-11-09")).toBe("9/nov");
  });
  it("counts days", () => {
    expect(daysBetween("2026-11-09", "2026-11-10")).toBe(1);
  });
  it("uses Brazil's day", () => {
    expect(todayInBrazil(new Date("2026-11-11T01:00:00Z"))).toBe("2026-11-10");
  });
});
