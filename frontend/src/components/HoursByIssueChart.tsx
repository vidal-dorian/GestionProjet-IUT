import type { HoursByIssue } from "../api/dashboard";

interface Props {
  data: HoursByIssue;
}

function formatHours(hours: number): string {
  const rounded = Math.round(hours * 100) / 100;
  return `${rounded} h`;
}

export default function HoursByIssueChart({ data }: Props) {
  const rows = [
    ...data.items.map((item) => ({
      key: `issue-${item.issue_number}`,
      label: `#${item.issue_number} ${item.issue_title}`,
      hours: item.hours,
      url: item.issue_url,
    })),
    ...(data.unattached_hours > 0
      ? [{ key: "unattached", label: "Sans issue rattachée", hours: data.unattached_hours, url: null }]
      : []),
  ];
  const max = Math.max(1, ...rows.map((row) => row.hours));

  return (
    <div className="bar-chart" role="img" aria-label="Heures par issue GitHub">
      {rows.map((row) => {
        const widthPercent = (row.hours / max) * 100;
        return (
          <div className="bar-chart-row" key={row.key} title={`${row.label} : ${formatHours(row.hours)}`}>
            <span className="bar-chart-label">
              {row.url ? (
                <a href={row.url} target="_blank" rel="noreferrer">
                  {row.label}
                </a>
              ) : (
                row.label
              )}
            </span>
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
