import { useEffect, useState } from "react";
import { listContributors, type Contributor } from "../api/projects";

interface Props {
  projectId: number;
}

function formatHours(hours: number): string {
  const rounded = Math.round(hours * 10) / 10;
  return `${rounded} h`;
}

export default function ContributorsSection({ projectId }: Props) {
  const [contributors, setContributors] = useState<Contributor[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listContributors(projectId)
      .then(setContributors)
      .catch(() => setError("Impossible de charger les contributeurs pour le moment."));
  }, [projectId]);

  return (
    <section className="members-section">
      <h2>Contributeurs</h2>

      {error && <p className="error">{error}</p>}

      {contributors && contributors.length === 0 && (
        <p>Personne n'a encore saisi d'heures sur ce projet.</p>
      )}

      {contributors && contributors.length > 0 && (
        <ul className="member-list">
          {contributors.map((contributor) => (
            <li key={contributor.account_id}>
              <span className="member-name">{contributor.account_email}</span>
              <span className="member-hours">{formatHours(contributor.hours)}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
