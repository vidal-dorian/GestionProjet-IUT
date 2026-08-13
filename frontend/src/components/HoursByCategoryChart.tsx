import type { HoursByCategory } from "../api/dashboard";

interface Props {
  data: HoursByCategory;
}

function formatHours(hours: number): string {
  const rounded = Math.round(hours * 100) / 100;
  return `${rounded} h`;
}

export default function HoursByCategoryChart({ data }: Props) {
  const rows = [
    ...data.items.map((item) => ({
      key: `category-${item.category_id}`,
      label: item.category_name,
      hours: item.hours,
    })),
    ...(data.unattached_hours > 0
      ? [{ key: "unattached", label: "Sans catégorie", hours: data.unattached_hours }]
      : []),
  ];
  const max = Math.max(1, ...rows.map((row) => row.hours));

  return (
    <div className="bar-chart" role="img" aria-label="Heures par catégorie">
      {rows.map((row) => {
        const widthPercent = (row.hours / max) * 100;
        return (
          <div className="bar-chart-row" key={row.key} title={`${row.label} : ${formatHours(row.hours)}`}>
            <span className="bar-chart-label">{row.label}</span>
            <div className="bar-chart-track">
              <div className="bar-chart-fill" style={{ width: `${widthPercent}%` }} />
            </div>
            <span className="bar-chart-value">{formatHours(row.hours)}</span>
          </div>
        );
      })}
    </div>
  );
}
