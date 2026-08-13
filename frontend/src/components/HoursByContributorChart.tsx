import type { Contributor } from "../api/projects";

interface Props {
  contributors: Contributor[];
}

function formatHours(hours: number): string {
  const rounded = Math.round(hours * 100) / 100;
  return `${rounded} h`;
}

export default function HoursByContributorChart({ contributors }: Props) {
  const sorted = [...contributors].sort((a, b) => b.hours - a.hours);
  const max = Math.max(1, ...sorted.map((c) => c.hours));

  return (
    <div className="bar-chart" role="img" aria-label="Heures saisies par contributeur">
      {sorted.map((contributor) => {
        const widthPercent = (contributor.hours / max) * 100;
        return (
          <div
            className="bar-chart-row"
            key={contributor.account_id}
            title={`${contributor.account_email} : ${formatHours(contributor.hours)}`}
          >
            <span className="bar-chart-label">{contributor.account_email}</span>
            <div className="bar-chart-track">
              <div className="bar-chart-fill" style={{ width: `${widthPercent}%` }} />
            </div>
            <span className="bar-chart-value">{formatHours(contributor.hours)}</span>
          </div>
        );
      })}
    </div>
  );
}
