import { useState } from "react";
import { ApiError } from "../api/projects";
import { setIssueClosedOn, type BurndownIssue } from "../api/sprints";

interface Props {
  projectId: string;
  issues: BurndownIssue[];
  // Appelé après chaque enregistrement pour recharger la courbe.
  onChanged: () => void;
}

function formatDate(isoDate: string): string {
  return new Date(`${isoDate}T00:00:00`).toLocaleDateString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

/* Correction des dates de clôture : une US fermée sur GitHub avec un jour de
   retard fausserait la courbe. La date saisie prime sur celle de GitHub et
   survit aux synchronisations ; « Rétablir » revient à celle de GitHub. */
export default function BurndownClosureTable({ projectId, issues, onChanged }: Props) {
  const [error, setError] = useState<string | null>(null);

  async function save(issue: BurndownIssue, closedOn: string | null) {
    setError(null);
    try {
      await setIssueClosedOn(projectId, issue.id, closedOn);
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible d'enregistrer la date de clôture.");
    }
  }

  return (
    <div className="closure-table-wrapper">
      <h3>Dates de clôture des US</h3>
      <p className="meta">
        Si une US a été fermée en retard sur GitHub, corrige ici sa date de clôture : elle remplace celle de GitHub
        dans le burndown et les exports, et n'est pas écrasée par les synchronisations.
      </p>
      {error && <p className="error">{error}</p>}
      <div className="closure-table-scroll">
        <table className="closure-table">
          <thead>
            <tr>
              <th>US</th>
              <th>Points</th>
              <th>Clôture GitHub</th>
              <th>Date retenue</th>
            </tr>
          </thead>
          <tbody>
            {issues.map((issue) => (
              // La clé inclut la date retenue : après enregistrement, la ligne
              // repart de la valeur serveur au lieu de garder le brouillon.
              <ClosureRow key={`${issue.id}-${issue.effective_closed_on}`} issue={issue} onSave={save} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ClosureRow({
  issue,
  onSave,
}: {
  issue: BurndownIssue;
  onSave: (issue: BurndownIssue, closedOn: string | null) => Promise<void>;
}) {
  const [draft, setDraft] = useState(issue.effective_closed_on ?? "");
  const [saving, setSaving] = useState(false);
  const dirty = draft !== "" && draft !== issue.effective_closed_on;

  async function submit(closedOn: string | null) {
    setSaving(true);
    await onSave(issue, closedOn);
    setSaving(false);
  }

  return (
    <tr>
      <td>
        <a href={issue.url} target="_blank" rel="noreferrer">
          #{issue.number} {issue.title}
        </a>
      </td>
      <td>{issue.story_points ?? "—"}</td>
      <td>{issue.github_closed_on ? formatDate(issue.github_closed_on) : "Ouverte"}</td>
      <td>
        {issue.effective_closed_on ? (
          <div className="closure-cell">
            <input
              type="date"
              aria-label={`Date de clôture retenue pour #${issue.number}`}
              value={draft}
              disabled={saving}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && dirty) void submit(draft);
              }}
            />
            {dirty && (
              <button type="button" className="button-secondary" disabled={saving} onClick={() => void submit(draft)}>
                {saving ? "..." : "Enregistrer"}
              </button>
            )}
            {!dirty && issue.closed_on_override && (
              <>
                <span className="badge" title="Date saisie à la main">
                  modifiée
                </span>
                <button type="button" className="button-secondary" disabled={saving} onClick={() => void submit(null)}>
                  Rétablir
                </button>
              </>
            )}
          </div>
        ) : (
          <span className="meta">—</span>
        )}
      </td>
    </tr>
  );
}
