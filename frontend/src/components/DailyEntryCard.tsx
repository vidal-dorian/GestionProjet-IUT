import { useEffect, useState } from "react";
import { ApiError } from "../api/projects";
import type { DailyEntry, TeamMember } from "../api/reports";

interface Props {
  member: TeamMember;
  entry: DailyEntry | undefined;
  isMe: boolean;
  onSave: (answers: { done: string; todo: string; blockers: string }) => Promise<void>;
}

const QUESTIONS = [
  { key: "done", label: "Ce que j'ai fait depuis la dernière daily" },
  { key: "todo", label: "Ce que je vais faire aujourd'hui" },
  { key: "blockers", label: "Ce qui me bloque" },
] as const;

type Answers = Record<(typeof QUESTIONS)[number]["key"], string>;

function fromEntry(entry: DailyEntry | undefined): Answers {
  return { done: entry?.done ?? "", todo: entry?.todo ?? "", blockers: entry?.blockers ?? "" };
}

function formatTime(iso: string): string {
  // Horodatage stocké en UTC sans suffixe : on le lui rend avant conversion.
  const date = new Date(iso.endsWith("Z") ? iso : `${iso}Z`);
  return date.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}

/* Partie d'une personne dans le daily, enregistrée séparément des autres :
   chacun peut remplir la sienne en même temps sans écraser celle du voisin. */
export default function DailyEntryCard({ member, entry, isMe, onSave }: Props) {
  const [answers, setAnswers] = useState<Answers>(fromEntry(entry));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);

  // Reprend la version serveur quand elle change (enregistrement, rechargement),
  // sauf si l'utilisateur est en train de modifier la carte.
  useEffect(() => {
    if (!dirty) setAnswers(fromEntry(entry));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entry]);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await onSave(answers);
      setDirty(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible d'enregistrer pour le moment.");
    } finally {
      setSaving(false);
    }
  }

  const idPrefix = `daily-${member.account_id}`;

  return (
    <article className={isMe ? "daily-card is-me" : "daily-card"}>
      <header className="daily-card-header">
        <h3>
          {member.label}
          {member.roles.length > 0 && <span className="daily-card-role"> / {member.roles.join(", ")}</span>}
        </h3>
        {isMe && <span className="badge badge-member">Ta partie</span>}
      </header>

      {QUESTIONS.map((question, index) => (
        <div key={question.key} className="field">
          <label htmlFor={`${idPrefix}-${question.key}`}>
            {index + 1}. {question.label}
          </label>
          <textarea
            id={`${idPrefix}-${question.key}`}
            rows={2}
            maxLength={5000}
            value={answers[question.key]}
            placeholder={question.key === "blockers" ? "Rien (laisser vide)" : ""}
            onChange={(e) => {
              setAnswers((current) => ({ ...current, [question.key]: e.target.value }));
              setDirty(true);
            }}
          />
        </div>
      ))}

      {error && <p className="error">{error}</p>}
      <div className="daily-card-footer">
        <span className="meta">
          {dirty
            ? "Modifications non enregistrées"
            : entry
              ? `Enregistré${entry.updated_by_label ? ` par ${entry.updated_by_label}` : ""} à ${formatTime(entry.updated_at)}`
              : "Pas encore rempli"}
        </span>
        <button type="button" className="button-secondary" onClick={handleSave} disabled={saving || !dirty}>
          {saving ? "Enregistrement..." : "Enregistrer"}
        </button>
      </div>
    </article>
  );
}
