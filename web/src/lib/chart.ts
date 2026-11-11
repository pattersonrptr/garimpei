/**
 * Geometry for the price chart: daily lows -> SVG coordinates. Pure, so the
 * chart renders on the server with no chart library and no client JavaScript.
 */

import type { DailyLow } from "@/lib/types";

export interface ChartBox {
  width: number;
  height: number;
  left: number; // room for the price labels
  right: number;
  top: number;
  bottom: number; // room for the date labels
}

export interface ChartPoint {
  day: string;
  price: number;
  x: number;
  y: number;
}

export interface ChartSeries {
  condition: string;
  points: ChartPoint[];
  path: string; // "M x y L x y ..."
}

export interface PriceChart {
  series: ChartSeries[];
  yTicks: { y: number; price: number }[];
  xLabels: { x: number; day: string }[];
  firstDay: string | null;
}

const DAY_MS = 86_400_000;

function dayNumber(day: string): number {
  return Math.round(Date.parse(`${day}T00:00:00Z`) / DAY_MS);
}

function dayString(n: number): string {
  return new Date(n * DAY_MS).toISOString().slice(0, 10);
}

/** Today in Brazil, as YYYY-MM-DD (the API's days are Brazil's days). */
export function todayInBrazil(now: Date = new Date()): string {
  return now.toLocaleDateString("sv-SE", { timeZone: "America/Sao_Paulo" });
}

/** Round price ticks: 3 to 5 steps of 1, 2, 5 or 10 times a power of ten. */
function niceTicks(min: number, max: number): number[] {
  if (min === max) {
    min = Math.max(0, min - 5);
    max = max + 5;
  }
  const rough = (max - min) / 4;
  const power = 10 ** Math.floor(Math.log10(rough));
  const step = [1, 2, 5, 10].map((m) => m * power).find((s) => s >= rough) ?? power * 10;
  const ticks = [];
  for (let t = Math.floor(min / step) * step; t <= max + step / 2; t += step) {
    ticks.push(Math.round(t * 100) / 100);
  }
  return ticks;
}

/**
 * The chart for the last `days` days ending today. The x axis always spans
 * the whole window, so a short history looks short instead of stretched.
 */
export function priceChart(
  lows: DailyLow[],
  box: ChartBox,
  today: string,
  days = 90,
): PriceChart {
  const end = dayNumber(today);
  const start = end - (days - 1);
  const inWindow = lows.filter((low) => dayNumber(low.day) >= start);
  const plotWidth = box.width - box.left - box.right;
  const plotHeight = box.height - box.top - box.bottom;
  const x = (day: string) => box.left + ((dayNumber(day) - start) / (days - 1)) * plotWidth;

  const prices = inWindow.map((low) => low.price);
  const ticks = prices.length ? niceTicks(Math.min(...prices), Math.max(...prices)) : [];
  const low = ticks[0] ?? 0;
  const high = ticks[ticks.length - 1] ?? 1;
  const y = (price: number) =>
    box.top + plotHeight - ((price - low) / (high - low || 1)) * plotHeight;

  const byCondition = new Map<string, DailyLow[]>();
  for (const item of inWindow) {
    byCondition.set(item.condition, [...(byCondition.get(item.condition) ?? []), item]);
  }
  const series = [...byCondition.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([condition, items]) => {
      const points = items
        .slice()
        .sort((a, b) => a.day.localeCompare(b.day))
        .map((item) => ({ day: item.day, price: item.price, x: x(item.day), y: y(item.price) }));
      const path = points
        .map((p, i) => `${i ? "L" : "M"}${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
        .join(" ");
      return { condition, points, path };
    });

  const labelDays = [start, start + Math.round((days - 1) / 2), end].map(dayString);
  return {
    series,
    yTicks: ticks.map((price) => ({ y: y(price), price })),
    xLabels: labelDays.map((day) => ({ x: x(day), day })),
    firstDay: inWindow.length
      ? inWindow.map((l) => l.day).sort()[0]
      : null,
  };
}

/** "9/nov" style short dates for the axis. */
export function shortDate(day: string): string {
  const [, month, date] = day.split("-").map(Number);
  const months = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
  return `${date}/${months[month - 1]}`;
}

/** Whole days between two YYYY-MM-DD dates. */
export function daysBetween(from: string, to: string): number {
  return dayNumber(to) - dayNumber(from);
}
