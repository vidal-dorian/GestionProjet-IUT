import type { ProjectStats } from "../api/dashboard";

interface Props {
  stats: ProjectStats;
}

export default function ProjectStatsTiles({ stats }: Props) {
  const tiles = [
    { label: "Total d'heures", value: `${stats.total_hours} h` },
    { label: "Membres actifs", value: `${stats.active_member_count} / ${stats.member_count}` },
    { label: "Entrées saisies", value: stats.entry_count },
    { label: "Moyenne par membre", value: `${stats.average_hours_per_member} h` },
  ];

  return (
    <div className="stat-tiles">
      {tiles.map((tile) => (
        <div className="stat-tile" key={tile.label}>
          <span className="stat-tile-label">{tile.label}</span>
          <span className="stat-tile-value">{tile.value}</span>
        </div>
      ))}
    </div>
  );
}
