import type { RecentTimeEntry } from "../api/dashboard";

interface Props {
  entries: RecentTimeEntry[];
}

function formatDate(isoDate: string): string {
  return new Date(`${isoDate}T00:00:00`).toLocaleDateString("fr-FR");
}

export default function RecentEntriesList({ entries }: Props) {
  return (
    <ul className="entry-list">
      {entries.map((entry) => (
        <li key={entry.id}>
          <div className="entry-main">
            <span>
              <span className="entry-author">{entry.member_name}</span> — {formatDate(entry.date)}
            </span>
            <span className="entry-duration">{entry.duration_hours} h</span>
          </div>
          <p className="entry-description">{entry.description}</p>
        </li>
      ))}
    </ul>
  );
}
