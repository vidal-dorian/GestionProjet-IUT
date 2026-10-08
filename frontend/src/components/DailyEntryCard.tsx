import { useEffect, useRef, useState } from "react";
import { ApiError } from "../api/projects";
import type { DailyEntry, TeamMember } from "../api/reports";

interface Props {
  member: TeamMember;
  entry: DailyEntry | undefined;
  isMe: boolean;
  onSave: (answers: Answers) => Promise<void>;
}

const QUESTIONS = [
  { key: "done", label: "Ce que j'ai fait depuis la dernière daily" },
  { key: "todo", label: "Ce que je vais faire aujourd'hui" },
  { key: "blockers", label: "Ce qui me bloque" },
] as const;

export type Answers = Record<(typeof QUESTIONS)[number]["key"], string>;

// Délai sans frappe avant l'enregistrement automatique.
const AUTOSAVE_DELAY_MS = 800;

function fromEntry(entry: DailyEntry | undefined): Answers {
  return { done: entry?.done ?? "", todo: entry?.todo ?? "", blockers: entry?.blockers ?? "" };
}

function sameAnswers(a: Answers, b: Answers): boolean {
  return a.done === b.done && a.todo === b.todo && a.blockers === b.blockers;
}

function formatTime(iso: string): string {
  // Horodatage stocké en UTC sans suffixe : on le lui rend avant conversion.
  const date = new Date(iso.endsWith("Z") ? iso : `${iso}Z`);
  return date.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}

/* Partie d'une personne dans le daily. Chaque carte s'enregistre seule et
   automatiquement, indépendamment des autres : toute l'équipe peut remplir le
   daily en même temps. Les modifications faites ailleurs (arrivées par la
   synchronisation de la page) s'affichent tant qu'on n'est pas soi-même en
   train de modifier la carte. */
export default function DailyEntryCard({ member, entry, isMe, onSave }: Props) {
  const [answers, setAnswers] = useState<Answers>(fromEntry(entry));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Dernière valeur connue côté serveur : la carte est "à enregistrer" tant
  // que la saisie en diffère.
  const savedRef = useRef<Answers>(fromEntry(entry));
  const answersRef = useRef(answers);
  const inFlightRef = useRef(false);
  answersRef.current = answers;
  const dirty = !sameAnswers(answers, savedRef.current);

  useEffect(() => {
    const remote = fromEntry(entry);
    if (sameAnswers(remote, savedRef.current)) return;
    const hasLocalChanges = !sameAnswers(answersRef.current, savedRef.current);
    savedRef.current = remote;
    // Une saisie locale en cours l'emporte : elle sera enregistrée par-dessus.
    if (!hasLocalChanges) setAnswers(remote);
  }, [entry]);

  async function save() {
    if (inFlightRef.current) return;
    const snapshot = answersRef.current;
    if (sameAnswers(snapshot, savedRef.current)) return;
    inFlightRef.current = true;
    setSaving(true);
    setError(null);
    try {
      await onSave(snapshot);
      savedRef.current = snapshot;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Enregistrement impossible pour le moment.");
    } finally {
      inFlightRef.current = false;
      setSaving(false);
    }
    // Saisie poursuivie pendant l'enregistrement : on enchaîne.
    if (!sameAnswers(answersRef.current, savedRef.current)) setAnswers((current) => ({ ...current }));
  }

  useEffect(() => {
    if (!dirty || error) return;
    const timer = window.setTimeout(() => void save(), AUTOSAVE_DELAY_MS);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [answers, dirty, error]);

  // En quittant la page avant la fin du délai, on enregistre quand même.
  useEffect(
    () => () => {
      if (!sameAnswers(answersRef.current, savedRef.current)) void onSave(answersRef.current).catch(() => {});
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  const idPrefix = `daily-${member.account_id}`;

  let status: string;
  if (error) status = error;
  else if (saving) status = "Enregistrement...";
  else if (dirty) status = "Modifications en cours...";
  else if (entry)
    status = `Enregistré${entry.updated_by_label ? ` par ${entry.updated_by_label}` : ""} à ${formatTime(entry.updated_at)}`;
  else status = "Pas encore rempli";

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
              const value = e.target.value;
              setError(null);
              setAnswers((current) => ({ ...current, [question.key]: value }));
            }}
            onBlur={() => void save()}
          />
        </div>
      ))}

      <div className="daily-card-footer">
        <span className={error ? "error" : "meta"} role="status">
          {status}
        </span>
        {error && (
          <button type="button" className="button-secondary" onClick={() => void save()}>
            Réessayer
          </button>
        )}
      </div>
    </article>
  );
}
