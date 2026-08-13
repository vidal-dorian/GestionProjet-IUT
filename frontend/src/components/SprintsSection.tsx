import { type FormEvent, useEffect, useState } from "react";
import { ApiError } from "../api/projects";
import { createSprint, listSprints, type Sprint } from "../api/sprints";

interface Props {
  projectId: number;
}

function formatDate(isoDate: string): string {
  return new Date(isoDate).toLocaleDateString("fr-FR", { timeZone: "UTC" });
}

export default function SprintsSection({ projectId }: Props) {
  const [sprints, setSprints] = useState<Sprint[] | null>(null);
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
      const result = await createSprint(projectId, { name: name.trim(), start_date: startDate, end_date: endDate });
      if (result.overlap_warning) {
        setWarning(result.overlap_warning);
      }
      setName("");
      setStartDate("");
      setEndDate("");
      await loadSprints();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible de créer ce sprint pour le moment.");
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

        {error && <p className="error">{error}</p>}
        {warning && <p className="meta">⚠ {warning}</p>}

        <button type="submit" disabled={submitting}>
          {submitting ? "Création..." : "Créer le sprint"}
        </button>
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
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
