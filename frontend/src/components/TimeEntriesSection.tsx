import { type FormEvent, useEffect, useState } from "react";
import { ApiError, type GithubIssue, listGithubIssues } from "../api/projects";
import { listSprints, type Sprint } from "../api/sprints";
import { createTimeEntry, deleteTimeEntry, listMyTimeEntries, updateTimeEntry, type TimeEntry } from "../api/timeEntries";

interface Props {
  projectId: number;
}

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function formatDate(isoDate: string): string {
  return new Date(isoDate).toLocaleDateString("fr-FR", { timeZone: "UTC" });
}

function formatIssueLabel(issue: { number: number; title: string }): string {
  return `#${issue.number} ${issue.title}`;
}

function formatTotalHours(entries: TimeEntry[]): number {
  const total = entries.reduce((sum, entry) => sum + entry.duration_hours, 0);
  return Math.round(total * 100) / 100;
}

export default function TimeEntriesSection({ projectId }: Props) {
  const [entries, setEntries] = useState<TimeEntry[] | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [date, setDate] = useState(today());
  const [duration, setDuration] = useState("");
  const [description, setDescription] = useState("");
  const [issueSearch, setIssueSearch] = useState("");
  const [issues, setIssues] = useState<GithubIssue[]>([]);
  const [sprints, setSprints] = useState<Sprint[]>([]);
  const [sprintId, setSprintId] = useState<number | "">("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function loadEntries() {
    return listMyTimeEntries(projectId).then(setEntries);
  }

  useEffect(() => {
    loadEntries().catch(() => setError("Impossible de charger l'historique pour le moment."));
    listGithubIssues(projectId)
      .then(setIssues)
      .catch(() => setIssues([]));
    listSprints(projectId)
      .then((loadedSprints) => {
        setSprints(loadedSprints);
        setSprintId(suggestSprintForDate(today(), loadedSprints));
      })
      .catch(() => setSprints([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  function suggestSprintForDate(isoDate: string, sprintList: Sprint[]): number | "" {
    const found = sprintList.find((sprint) => sprint.start_date <= isoDate && isoDate <= sprint.end_date);
    return found ? found.id : "";
  }

  function handleDateChange(newDate: string) {
    setDate(newDate);
    setSprintId(suggestSprintForDate(newDate, sprints));
  }

  function resetForm() {
    setEditingId(null);
    setDate(today());
    setDuration("");
    setDescription("");
    setIssueSearch("");
    setSprintId(suggestSprintForDate(today(), sprints));
  }

  function startEditing(entry: TimeEntry) {
    setError(null);
    setEditingId(entry.id);
    setDate(entry.date);
    setDuration(String(entry.duration_hours));
    setDescription(entry.description);
    setIssueSearch(entry.github_issue ? formatIssueLabel(entry.github_issue) : "");
    setSprintId(entry.sprint_id ?? "");
  }

  async function handleDelete(entryId: number) {
    if (!window.confirm("Supprimer cette entrée ? Cette action est irréversible.")) return;
    try {
      await deleteTimeEntry(projectId, entryId);
      if (editingId === entryId) resetForm();
      await loadEntries();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible de supprimer cette entrée pour le moment.");
    }
  }

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

    const matchedIssue = issues.find((issue) => formatIssueLabel(issue) === issueSearch.trim());
    const payload = {
      date,
      duration_hours: durationHours,
      description: description.trim(),
      github_issue_id: matchedIssue ? matchedIssue.id : null,
      sprint_id: sprintId === "" ? null : sprintId,
    };

    setSubmitting(true);
    try {
      if (editingId) {
        await updateTimeEntry(projectId, editingId, payload);
      } else {
        await createTimeEntry(projectId, payload);
      }
      resetForm();
      await loadEntries();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible d'enregistrer cette entrée pour le moment.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="time-entries-section">
      <h2>{editingId ? "Modifier l'entrée" : "Saisir une entrée de temps"}</h2>

      <form onSubmit={handleSubmit} className="form form-inline">
        <label htmlFor="entry-date">Date</label>
        <input id="entry-date" type="date" value={date} onChange={(e) => handleDateChange(e.target.value)} />

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

        {sprints.length > 0 && (
          <>
            <label htmlFor="entry-sprint">Sprint (facultatif)</label>
            <select
              id="entry-sprint"
              value={sprintId}
              onChange={(e) => setSprintId(e.target.value ? Number(e.target.value) : "")}
            >
              <option value="">Aucun</option>
              {sprints.map((sprint) => (
                <option key={sprint.id} value={sprint.id}>
                  {sprint.name}
                </option>
              ))}
            </select>
          </>
        )}

        {issues.length > 0 && (
          <>
            <label htmlFor="entry-issue">Issue GitHub (facultatif)</label>
            <input
              id="entry-issue"
              type="text"
              list="entry-issue-options"
              value={issueSearch}
              onChange={(e) => setIssueSearch(e.target.value)}
              placeholder="Rechercher par numéro ou titre..."
            />
            <datalist id="entry-issue-options">
              {issues.map((issue) => (
                <option key={issue.id} value={formatIssueLabel(issue)} />
              ))}
            </datalist>
          </>
        )}

        {error && <p className="error">{error}</p>}

        <div className="form-actions">
          <button type="submit" disabled={submitting}>
            {submitting ? "Enregistrement..." : editingId ? "Mettre à jour" : "Enregistrer"}
          </button>
          {editingId && (
            <button type="button" className="button-secondary" onClick={resetForm}>
              Annuler
            </button>
          )}
        </div>
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
              {entry.github_issue && (
                <p className="meta">
                  Issue :{" "}
                  <a href={entry.github_issue.url} target="_blank" rel="noreferrer">
                    {formatIssueLabel(entry.github_issue)}
                  </a>
                </p>
              )}
              {entry.sprint && <p className="meta">Sprint : {entry.sprint.name}</p>}
              <div className="entry-actions">
                <button type="button" className="link-button" onClick={() => startEditing(entry)}>
                  Modifier
                </button>
                <button type="button" className="link-button" onClick={() => handleDelete(entry.id)}>
                  Supprimer
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
