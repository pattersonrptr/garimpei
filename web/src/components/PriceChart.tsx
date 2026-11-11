import { daysBetween, priceChart, shortDate, todayInBrazil } from "@/lib/chart";
import { formatPrice } from "@/lib/format";
import type { DailyLow } from "@/lib/types";

/**
 * Two drawings of the same chart: SVG text scales with the drawing, so a wide
 * chart squeezed onto a phone has unreadable labels. CSS shows one of them.
 */
const WIDE = { width: 640, height: 240, left: 64, right: 12, top: 12, bottom: 28 };
const NARROW = { width: 340, height: 220, left: 56, right: 10, top: 12, bottom: 28 };
const DAYS = 90;

type Box = typeof WIDE;

/**
 * Green and red mean good or expensive price only (Phase 0 rule), so the two
 * lines are ink (used, the highlight) and muted, dashed (new).
 */
const STYLE: Record<string, { label: string; className: string }> = {
  used: { label: "Usado (menor preço do dia)", className: "line-used" },
  new: { label: "Novo (menor preço do dia)", className: "line-new" },
};

export function PriceChart({ lows }: { lows: DailyLow[] }) {
  const today = todayInBrazil();
  const chart = priceChart(lows, WIDE, today, DAYS);
  const series = chart.series.filter((s) => STYLE[s.condition]);

  if (series.length === 0) {
    return (
      <section className="chart">
        <h2>Histórico de preço</h2>
        <p className="muted">Ainda não temos preços registrados para este livro.</p>
      </section>
    );
  }

  const historyDays = chart.firstDay ? daysBetween(chart.firstDay, today) + 1 : 0;
  return (
    <section className="chart">
      <h2>Histórico de preço</h2>
      <p className="muted small">Últimos {DAYS} dias</p>
      <ChartSvg lows={lows} box={NARROW} today={today} className="chart-narrow" />
      <ChartSvg lows={lows} box={WIDE} today={today} className="chart-wide" />
      <ul className="legend">
        {series.map((s) => (
          <li key={s.condition} className={STYLE[s.condition].className}>
            <svg width="24" height="10" aria-hidden="true">
              <line x1="0" x2="24" y1="5" y2="5" />
            </svg>
            {STYLE[s.condition].label}
          </li>
        ))}
      </ul>
      {historyDays < 14 && (
        <p className="muted small">
          Começamos a acompanhar este livro há {historyDays}{" "}
          {historyDays === 1 ? "dia" : "dias"}. O gráfico fica mais útil com o tempo.
        </p>
      )}
    </section>
  );
}

function ChartSvg({
  lows,
  box,
  today,
  className,
}: {
  lows: DailyLow[];
  box: Box;
  today: string;
  className: string;
}) {
  const chart = priceChart(lows, box, today, DAYS);
  const series = chart.series.filter((s) => STYLE[s.condition]);
  const summary = describe(series);
  return (
    <svg
      viewBox={`0 0 ${box.width} ${box.height}`}
      className={className}
      role="img"
      aria-labelledby={`${className}-title ${className}-desc`}
      preserveAspectRatio="xMidYMid meet"
    >
      <title id={`${className}-title`}>Histórico do menor preço por dia</title>
      <desc id={`${className}-desc`}>{summary}</desc>
      {chart.yTicks.map((tick) => (
        <g key={tick.price}>
          <line
            className="grid"
            x1={box.left}
            x2={box.width - box.right}
            y1={tick.y}
            y2={tick.y}
          />
          <text className="axis" x={box.left - 8} y={tick.y + 4} textAnchor="end">
            {formatPrice(tick.price).replace(/,00$/, "")}
          </text>
        </g>
      ))}
      {chart.xLabels.map((label, i) => (
        <text
          key={label.day}
          className="axis"
          x={label.x}
          y={box.height - 6}
          textAnchor={i === 0 ? "start" : i === chart.xLabels.length - 1 ? "end" : "middle"}
        >
          {shortDate(label.day)}
        </text>
      ))}
      {series.map((s) => (
        <g key={s.condition} className={STYLE[s.condition].className}>
          <path d={s.path} fill="none" />
          {s.points.map((p) => (
            <circle key={p.day} cx={p.x} cy={p.y} r={3}>
              <title>{`${shortDate(p.day)}: ${formatPrice(p.price)}`}</title>
            </circle>
          ))}
        </g>
      ))}
    </svg>
  );
}

function describe(series: { condition: string; points: { price: number }[] }[]): string {
  return series
    .map((s) => {
      const prices = s.points.map((p) => p.price);
      return `${STYLE[s.condition].label}: de ${formatPrice(Math.min(...prices))} a ${formatPrice(Math.max(...prices))}`;
    })
    .join("; ");
}
