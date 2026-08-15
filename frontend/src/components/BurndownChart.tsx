import type { BurndownPoint } from "../api/sprints";

interface Props {
  ideal: BurndownPoint[];
  actual: BurndownPoint[];
  totalPoints: number;
}

const WIDTH = 640;
const HEIGHT = 240;
const PADDING_LEFT = 44;
const PADDING_RIGHT = 12;
const PADDING_TOP = 20;
const PADDING_BOTTOM = 40;
const INNER_WIDTH = WIDTH - PADDING_LEFT - PADDING_RIGHT;
const INNER_HEIGHT = HEIGHT - PADDING_TOP - PADDING_BOTTOM;

function toMs(isoDate: string): number {
  return new Date(`${isoDate}T00:00:00`).getTime();
}

function formatDate(isoDate: string): string {
  return new Date(`${isoDate}T00:00:00`).toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit" });
}

export default function BurndownChart({ ideal, actual, totalPoints }: Props) {
  const startDate = ideal[0]?.date;
  const endDate = ideal[ideal.length - 1]?.date;
  if (!startDate || !endDate) return null;

  const startMs = toMs(startDate);
  const spanMs = Math.max(toMs(endDate) - startMs, 1);
  const yMax = Math.max(totalPoints, 1);

  function toXY(point: BurndownPoint) {
    const x = PADDING_LEFT + ((toMs(point.date) - startMs) / spanMs) * INNER_WIDTH;
    const y = PADDING_TOP + INNER_HEIGHT - (point.remaining_points / yMax) * INNER_HEIGHT;
    return { x, y };
  }

  function toPathD(points: BurndownPoint[]): string {
    return points
      .map((point, i) => {
        const { x, y } = toXY(point);
        return `${i === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
      })
      .join(" ");
  }

  return (
    <div className="line-chart">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Burndown du sprint : story points restants par jour">
        {[0, 0.5, 1].map((fraction) => {
          const y = PADDING_TOP + INNER_HEIGHT * (1 - fraction);
          return (
            <g key={fraction}>
              <line x1={PADDING_LEFT} y1={y} x2={WIDTH - PADDING_RIGHT} y2={y} className="line-chart-grid" />
              <text x={PADDING_LEFT - 10} y={y} className="line-chart-axis-label" textAnchor="end" dy="0.32em">
                {Math.round(yMax * fraction)}
              </text>
            </g>
          );
        })}

        <text x={PADDING_LEFT} y={HEIGHT - PADDING_BOTTOM + 28} className="line-chart-axis-label" textAnchor="start">
          {formatDate(startDate)}
        </text>
        <text x={WIDTH - PADDING_RIGHT} y={HEIGHT - PADDING_BOTTOM + 28} className="line-chart-axis-label" textAnchor="end">
          {formatDate(endDate)}
        </text>

        <path d={toPathD(ideal)} className="burndown-line-ideal" fill="none" />
        <path d={toPathD(actual)} className="burndown-line-actual" fill="none" />

        {actual.map((point) => {
          const { x, y } = toXY(point);
          return <circle key={point.date} cx={x} cy={y} r={4} className="line-chart-dot" />;
        })}
      </svg>

      <div className="burndown-legend">
        <span className="burndown-legend-item">
          <span className="burndown-legend-swatch burndown-legend-swatch-actual" aria-hidden="true" />
          Réel
        </span>
        <span className="burndown-legend-item">
          <span className="burndown-legend-swatch burndown-legend-swatch-ideal" aria-hidden="true" />
          Idéal
        </span>
      </div>
    </div>
  );
}
