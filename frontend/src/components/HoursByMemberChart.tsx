import type { Member } from "../api/members";

interface Props {
  members: Member[];
}

function formatHours(hours: number): string {
  const rounded = Math.round(hours * 100) / 100;
  return `${rounded} h`;
}

export default function HoursByMemberChart({ members }: Props) {
  const sorted = [...members].sort((a, b) => b.total_hours - a.total_hours);
  const max = Math.max(1, ...sorted.map((m) => m.total_hours));

  return (
    <div className="bar-chart" role="img" aria-label="Heures saisies par membre">
      {sorted.map((member) => {
        const widthPercent = (member.total_hours / max) * 100;
        return (
          <div className="bar-chart-row" key={member.id} title={`${member.name} : ${formatHours(member.total_hours)}`}>
            <span className="bar-chart-label">{member.name}</span>
            <div className="bar-chart-track">
              <div className="bar-chart-fill" style={{ width: `${widthPercent}%` }} />
            </div>
            <span className="bar-chart-value">{formatHours(member.total_hours)}</span>
          </div>
        );
      })}
    </div>
  );
}
