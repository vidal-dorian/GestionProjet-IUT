import { FormEvent, useEffect, useState } from "react";
import { ApiError } from "../api/projects";
import { createTimeEntry, listMyTimeEntries, type TimeEntry } from "../api/timeEntries";

interface Props {
  projectId: number;
}

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function formatDate(isoDate: string): string {
  return new Date(isoDate).toLocaleDateString("fr-FR", { timeZone: "UTC" });
}

function formatTotalHours(entries: TimeEntry[]): number {
  const total = entries.reduce((sum, entry) => sum + entry.duration_hours, 0);
  return Math.round(total * 100) / 100;
}

export default function TimeEntriesSection({ projectId }: Props) {
  const [entries, setEntries] = useState<TimeEntry[] | null>(null);
  const [date, setDate] = useState(today());
  const [duration, setDuration] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function loadEntries() {
    return listMyTimeEntries(projectId).then(setEntries);
  }

  useEffect(() => {
    loadEntries().catch(() => setError("Impossible de charger l'historique pour le moment."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const durationHours = Number(duration.replace(",", "."));
    if (!date) {
      setError("La date est obligatoire.");
      return;
    }
    if (!Number.isFinite(durationHours) || durationHours <= 0 || durationHours > 24) {
      setError("La durée doit être un nombre d'heures strictement positif, au maximum 24.");
      return;
    }
    if (!description.trim()) {
      setError("La description est obligatoire.");
      return;
    }

    setSubmitting(true);
    try {
      await createTimeEntry(projectId, { date, duration_hours: durationHours, description: description.trim() });
      setDate(today());
      setDuration("");
      setDescription("");
      await loadEntries();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible d'enregistrer cette entrée pour le moment.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="time-entries-section">
      <h2>Saisir une entrée de temps</h2>

      <form onSubmit={handleSubmit} className="form form-inline">
        <label htmlFor="entry-date">Date</label>
        <input id="entry-date" type="date" value={date} onChange={(e) => setDate(e.target.value)} />

        <label htmlFor="entry-duration">Durée (heures)</label>
        <input
          id="entry-duration"
          type="number"
          inputMode="decimal"
          step="0.25"
          value={duration}
          onChange={(e) => setDuration(e.target.value)}
        />

        <label htmlFor="entry-description">Description</label>
        <textarea
          id="entry-description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
        />

        {error && <p className="error">{error}</p>}

        <button type="submit" disabled={submitting}>
          {submitting ? "Enregistrement..." : "Enregistrer"}
        </button>
      </form>

      <div className="page-header">
        <h2>Mes entrées</h2>
        {entries && (
          <span className="meta">Total : {formatTotalHours(entries)} h sur ce projet</span>
        )}
      </div>

      {entries && entries.length === 0 && <p>Aucune entrée pour l'instant.</p>}

      {entries && entries.length > 0 && (
        <ul className="entry-list">
          {entries.map((entry) => (
            <li key={entry.id}>
              <div className="entry-main">
                <span className="entry-date">{formatDate(entry.date)}</span>
                <span className="entry-duration">{entry.duration_hours} h</span>
              </div>
              <p className="entry-description">{entry.description}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
