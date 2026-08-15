import type { Sprint } from "../api/sprints";

interface Props {
  sprints: Sprint[];
}

function toMs(isoDate: string): number {
  return new Date(`${isoDate}T00:00:00`).getTime();
}

function formatDate(isoDate: string): string {
  return new Date(`${isoDate}T00:00:00`).toLocaleDateString("fr-FR");
}

export default function GanttChart({ sprints }: Props) {
  if (sprints.length === 0) {
    return <p>Aucun sprint pour l'instant.</p>;
  }

  const sorted = [...sprints].sort((a, b) => toMs(a.start_date) - toMs(b.start_date));
  const minMs = Math.min(...sorted.map((sprint) => toMs(sprint.start_date)));
  const maxMs = Math.max(...sorted.map((sprint) => toMs(sprint.end_date)));
  const spanMs = Math.max(maxMs - minMs, 1);

  return (
    <div className="gantt-chart">
      {sorted.map((sprint) => {
        const startPercent = ((toMs(sprint.start_date) - minMs) / spanMs) * 100;
        const widthPercent = Math.max(((toMs(sprint.end_date) - toMs(sprint.start_date)) / spanMs) * 100, 1.5);
        return (
          <div key={sprint.id} className="gantt-row">
            <span className="gantt-row-label">{sprint.name}</span>
            <div className="gantt-row-track">
              <div
                className="gantt-row-bar"
                style={{ marginLeft: `${startPercent}%`, width: `${widthPercent}%` }}
              />
            </div>
            <span className="gantt-row-dates">
              {formatDate(sprint.start_date)} → {formatDate(sprint.end_date)}
            </span>
          </div>
        );
      })}
    </div>
  );
}
