import { type FormEvent, type ReactNode, useState } from "react";
import { ApiError } from "../api/projects";

interface Props {
  name: string;
  inputLabel: string;
  maxLength: number;
  onRename: (name: string) => Promise<void>;
  /** Actions supplémentaires affichées à côté de "Renommer" (ex. suppression). */
  extraActions?: ReactNode;
}

/* Ligne de liste renommable sur place : sert à corriger une faute (un accent
   oublié...) sans supprimer puis recréer l'élément, ce qui détacherait les
   heures ou les rôles qui y sont rattachés. */
export default function RenamableListItem({ name, inputLabel, maxLength, onRename, extraActions }: Props) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(name);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function startEditing() {
    setValue(name);
    setError(null);
    setEditing(true);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = value.trim();
    if (!trimmed) {
      setError("Le nom est obligatoire.");
      return;
    }
    if (trimmed === name) {
      setEditing(false);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onRename(trimmed);
      setEditing(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible de renommer pour le moment.");
    } finally {
      setSaving(false);
    }
  }

  if (!editing) {
    return (
      <li>
        <span>{name}</span>
        <span className="member-actions">
          <button type="button" className="button-secondary" onClick={startEditing}>
            Renommer
          </button>
          {extraActions}
        </span>
      </li>
    );
  }

  return (
    <li className="rename-row">
      <form onSubmit={handleSubmit} className="rename-form">
        <input
          type="text"
          aria-label={inputLabel}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          maxLength={maxLength}
          autoFocus
          onKeyDown={(e) => {
            if (e.key === "Escape") setEditing(false);
          }}
        />
        <span className="member-actions">
          <button type="submit" className="button-secondary" disabled={saving}>
            {saving ? "Enregistrement..." : "Enregistrer"}
          </button>
          <button type="button" className="link-button" onClick={() => setEditing(false)}>
            Annuler
          </button>
        </span>
      </form>
      {error && <p className="error">{error}</p>}
    </li>
  );
}
