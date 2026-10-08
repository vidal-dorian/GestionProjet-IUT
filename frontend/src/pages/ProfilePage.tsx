import { type FormEvent, useState } from "react";
import { updateMyDisplayName } from "../api/auth";
import { ApiError } from "../api/projects";
import AppShell from "../components/AppShell";
import PageHeader from "../components/PageHeader";
import { useAuth } from "../context/AuthContext";

export default function ProfilePage() {
  const { account, refresh } = useAuth();
  const [displayName, setDisplayName] = useState(account?.display_name ?? "");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      const updated = await updateMyDisplayName(displayName);
      setDisplayName(updated.display_name ?? "");
      await refresh();
      setSaved(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible d'enregistrer ton nom pour le moment.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <AppShell title="Mon profil">
      <div className="page">
        <PageHeader title="Mon profil" subtitle={account?.email} />

        <form onSubmit={handleSubmit} className="form">
          <label htmlFor="display-name">Nom affiché</label>
          <input
            id="display-name"
            type="text"
            value={displayName}
            onChange={(e) => {
              setDisplayName(e.target.value);
              setSaved(false);
            }}
            maxLength={120}
            placeholder="NOM Prénom"
          />
          <p className="meta">
            Utilisé dans les comptes-rendus (daily, review...) à la place de ton adresse e-mail. Format conseillé :
            « VIDAL Dorian ».
          </p>

          {error && <p className="error">{error}</p>}

          <button type="submit" disabled={saving}>
            {saving ? "Enregistrement..." : "Enregistrer"}
          </button>
          {saved && <p className="meta">Nom enregistré.</p>}
        </form>
      </div>
    </AppShell>
  );
}
