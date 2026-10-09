import { type FormEvent, useEffect, useState } from "react";
import { ApiError } from "../api/projects";
import { createSprint, listSprints, type Sprint, updateSprint } from "../api/sprints";

interface Props {
  projectId: number;
}

function formatDate(isoDate: string): string {
  return new Date(isoDate).toLocaleDateString("fr-FR", { timeZone: "UTC" });
}

export default function SprintsSection({ projectId }: Props) {
  const [sprints, setSprints] = useState<Sprint[] | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [name, setName] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function loadSprints() {
    return listSprints(projectId).then(setSprints);
  }

  useEffect(() => {
    loadSprints().catch(() => setError("Impossible de charger les sprints pour le moment."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  function resetForm() {
    setEditingId(null);
    setName("");
    setStartDate("");
    setEndDate("");
    setError(null);
  }

  function startEditing(sprint: Sprint) {
    setEditingId(sprint.id);
    setName(sprint.name);
    setStartDate(sprint.start_date);
    setEndDate(sprint.end_date);
    setError(null);
    setWarning(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setWarning(null);

    if (!name.trim()) {
      setError("Le nom du sprint est obligatoire.");
      return;
    }
    if (!startDate || !endDate) {
      setError("Les dates de début et de fin sont obligatoires.");
      return;
    }
    if (endDate <= startDate) {
      setError("La date de fin doit être postérieure à la date de début.");
      return;
    }

    setSubmitting(true);
    try {
      const input = { name: name.trim(), start_date: startDate, end_date: endDate };
      const result = editingId
        ? await updateSprint(projectId, editingId, input)
        : await createSprint(projectId, input);
      if (result.overlap_warning) {
        setWarning(result.overlap_warning);
      }
      resetForm();
      await loadSprints();
    } catch (err) {
      const fallback = editingId
        ? "Impossible de modifier ce sprint pour le moment."
        : "Impossible de créer ce sprint pour le moment.";
      setError(err instanceof ApiError ? err.message : fallback);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="chart-section">
      <h2>Sprints</h2>

      <form onSubmit={handleSubmit} className="form form-inline">
        <label htmlFor="sprint-name">Nom du sprint</label>
        <input id="sprint-name" type="text" value={name} onChange={(e) => setName(e.target.value)} maxLength={120} />

        <label htmlFor="sprint-start">Date de début</label>
        <input id="sprint-start" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />

        <label htmlFor="sprint-end">Date de fin</label>
        <input id="sprint-end" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />

        {editingId && (
          <p className="meta">
            Le burndown d'un sprint repose sur l'itération du GitHub Project (ou le label GitHub) portant son nom
            (casse, accents, espaces et tirets ignorés) : pensez à la renommer si vous renommez le sprint.
          </p>
        )}

        {error && <p className="error">{error}</p>}
        {warning && <p className="meta">⚠ {warning}</p>}

        <div className="form-actions">
          <button type="submit" disabled={submitting}>
            {submitting ? "Enregistrement..." : editingId ? "Mettre à jour" : "Créer le sprint"}
          </button>
          {editingId && (
            <button type="button" className="button-secondary" onClick={resetForm}>
              Annuler
            </button>
          )}
        </div>
      </form>

      {sprints && sprints.length === 0 && <p>Aucun sprint pour l'instant.</p>}

      {sprints && sprints.length > 0 && (
        <ul className="member-list">
          {sprints.map((sprint) => (
            <li key={sprint.id}>
              <span>{sprint.name}</span>
              <span className="meta">
                {formatDate(sprint.start_date)} → {formatDate(sprint.end_date)}
              </span>
              <button
                type="button"
                className="link-button"
                onClick={() => startEditing(sprint)}
                disabled={submitting}
                aria-label={`Modifier ${sprint.name}`}
              >
                {editingId === sprint.id ? "En cours de modification" : "Modifier"}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
