import { useState } from "react";
import type { HoursOverTime } from "../api/dashboard";

interface Props {
  data: HoursOverTime;
}

const WIDTH = 640;
const HEIGHT = 220;
const PADDING_LEFT = 36;
const PADDING_RIGHT = 12;
const PADDING_TOP = 16;
const PADDING_BOTTOM = 28;
const INNER_WIDTH = WIDTH - PADDING_LEFT - PADDING_RIGHT;
const INNER_HEIGHT = HEIGHT - PADDING_TOP - PADDING_BOTTOM;
const MAX_X_LABELS = 7;

function niceMax(value: number): number {
  if (value <= 0) return 1;
  const magnitude = Math.pow(10, Math.floor(Math.log10(value)));
  const normalized = value / magnitude;
  const step = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10;
  return step * magnitude;
}

function formatPeriod(period: string, granularity: "day" | "week"): string {
  const date = new Date(`${period}T00:00:00`);
  const short = date.toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit" });
  return granularity === "week" ? `Sem. ${short}` : short;
}

export default function HoursOverTimeChart({ data }: Props) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const { points, granularity } = data;

  const yMax = niceMax(Math.max(...points.map((p) => p.hours), 0));
  const xStep = points.length > 1 ? INNER_WIDTH / (points.length - 1) : 0;

  const coords = points.map((p, i) => ({
    x: PADDING_LEFT + i * xStep,
    y: PADDING_TOP + INNER_HEIGHT - (p.hours / yMax) * INNER_HEIGHT,
    ...p,
  }));

  const pathD = coords.map((c, i) => `${i === 0 ? "M" : "L"} ${c.x.toFixed(1)} ${c.y.toFixed(1)}`).join(" ");

  const labelEvery = Math.max(1, Math.ceil(points.length / MAX_X_LABELS));
  const last = coords[coords.length - 1];
  const hovered = hoverIndex !== null ? coords[hoverIndex] : null;

  return (
    <div className="line-chart">
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label="Évolution des heures saisies dans le temps"
        onMouseLeave={() => setHoverIndex(null)}
      >
        {[0, 0.5, 1].map((fraction) => {
          const y = PADDING_TOP + INNER_HEIGHT * (1 - fraction);
          return (
            <g key={fraction}>
              <line x1={PADDING_LEFT} y1={y} x2={WIDTH - PADDING_RIGHT} y2={y} className="line-chart-grid" />
              <text x={PADDING_LEFT - 8} y={y} className="line-chart-axis-label" textAnchor="end" dy="0.32em">
                {Math.round(yMax * fraction)}
              </text>
            </g>
          );
        })}

        {coords.map(
          (c, i) =>
            i % labelEvery === 0 && (
              <text
                key={c.period}
                x={c.x}
                y={HEIGHT - PADDING_BOTTOM + 16}
                className="line-chart-axis-label"
                textAnchor="middle"
              >
                {formatPeriod(c.period, granularity)}
              </text>
            ),
        )}

        <path d={pathD} className="line-chart-line" fill="none" />

        {last &&
          (coords.length > 1 ? (
            <text x={last.x} y={last.y - 10} className="line-chart-end-label" textAnchor="end">
              {last.hours} h
            </text>
          ) : (
            <text x={last.x + 10} y={last.y} className="line-chart-end-label" textAnchor="start" dy="0.32em">
              {last.hours} h
            </text>
          ))}

        {coords.map((c, i) => (
          <rect
            key={c.period}
            x={c.x - xStep / 2}
            y={PADDING_TOP}
            width={Math.max(xStep, 1)}
            height={INNER_HEIGHT}
            fill="transparent"
            onMouseEnter={() => setHoverIndex(i)}
            onFocus={() => setHoverIndex(i)}
            tabIndex={0}
          />
        ))}

        {hovered && (
          <>
            <line
              x1={hovered.x}
              y1={PADDING_TOP}
              x2={hovered.x}
              y2={HEIGHT - PADDING_BOTTOM}
              className="line-chart-crosshair"
            />
            <circle cx={hovered.x} cy={hovered.y} r={4} className="line-chart-dot" />
          </>
        )}
      </svg>

      {hovered && (
        <div className="line-chart-tooltip">
          <strong>{hovered.hours} h</strong> — {formatPeriod(hovered.period, granularity)}
        </div>
      )}
    </div>
  );
}
