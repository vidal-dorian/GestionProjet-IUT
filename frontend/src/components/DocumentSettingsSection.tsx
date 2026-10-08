import { type ChangeEvent, type FormEvent, useEffect, useState } from "react";
import {
  deleteLogo,
  fetchLogoObjectUrl,
  getDocumentSettings,
  type LogoPosition,
  updateDocumentFooter,
  uploadLogo,
} from "../api/documentSettings";
import { ApiError } from "../api/projects";

interface Props {
  projectId: number;
  projectName: string;
}

const POSITIONS: { key: LogoPosition; label: string }[] = [
  { key: "left", label: "Logo de gauche" },
  { key: "right", label: "Logo de droite" },
];

const MAX_LOGO_BYTES = 1024 * 1024;

export default function DocumentSettingsSection({ projectId, projectName }: Props) {
  const [footer, setFooter] = useState("");
  const [logoUrls, setLogoUrls] = useState<Partial<Record<LogoPosition, string>>>({});
  const [loaded, setLoaded] = useState(false);
  const [savingFooter, setSavingFooter] = useState(false);
  const [footerSaved, setFooterSaved] = useState(false);
  const [busyPosition, setBusyPosition] = useState<LogoPosition | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refreshLogos(positions: LogoPosition[]) {
    const entries = await Promise.all(
      positions.map(async (position) => [position, await fetchLogoObjectUrl(projectId, position)] as const),
    );
    setLogoUrls((current) => {
      Object.values(current).forEach((url) => url && URL.revokeObjectURL(url));
      return Object.fromEntries(entries);
    });
  }

  useEffect(() => {
    getDocumentSettings(projectId)
      .then(async (settings) => {
        setFooter(settings.footer);
        await refreshLogos(settings.logos);
      })
      .catch(() => setError("Impossible de charger les réglages des documents pour le moment."))
      .finally(() => setLoaded(true));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  async function handleFooterSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSavingFooter(true);
    setFooterSaved(false);
    setError(null);
    try {
      const settings = await updateDocumentFooter(projectId, footer);
      setFooter(settings.footer);
      setFooterSaved(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible d'enregistrer le pied de page.");
    } finally {
      setSavingFooter(false);
    }
  }

  async function handleUpload(position: LogoPosition, event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (file.size > MAX_LOGO_BYTES) {
      setError("Le logo ne doit pas dépasser 1 Mo.");
      return;
    }
    setBusyPosition(position);
    setError(null);
    try {
      const settings = await uploadLogo(projectId, position, file);
      await refreshLogos(settings.logos);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible d'envoyer ce logo.");
    } finally {
      setBusyPosition(null);
    }
  }

  async function handleDelete(position: LogoPosition) {
    setBusyPosition(position);
    setError(null);
    try {
      await deleteLogo(projectId, position);
      setLogoUrls((current) => {
        const next = { ...current };
        if (next[position]) URL.revokeObjectURL(next[position]);
        delete next[position];
        return next;
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible de supprimer ce logo.");
    } finally {
      setBusyPosition(null);
    }
  }

  if (!loaded) return <p>Chargement...</p>;

  return (
    <section className="chart-section">
      <h2>Documents exportés</h2>
      <p className="meta">
        Logos et pied de page des comptes-rendus Word de planification, review et rétrospective (le daily n'en a pas).
      </p>

      <form onSubmit={handleFooterSubmit} className="footer-form">
        <div className="field">
          <label htmlFor="document-footer">Pied de page</label>
          <input
            id="document-footer"
            type="text"
            value={footer}
            onChange={(e) => {
              setFooter(e.target.value);
              setFooterSaved(false);
            }}
            maxLength={255}
            placeholder={projectName}
          />
        </div>
        <button type="submit" className="button-secondary" disabled={savingFooter}>
          {savingFooter ? "Enregistrement..." : "Enregistrer"}
        </button>
      </form>
      <p className="meta">
        {footerSaved
          ? "Pied de page enregistré."
          : "Laisse vide pour utiliser le nom du projet. Le numéro de page (1/3...) est ajouté automatiquement à droite."}
      </p>

      <div className="logo-grid">
        {POSITIONS.map(({ key, label }) => (
          <div key={key} className="logo-slot">
            <p className="logo-slot-label">{label}</p>
            <div className="logo-preview">
              {logoUrls[key] ? <img src={logoUrls[key]} alt={label} /> : <span className="meta">Aucun logo</span>}
            </div>
            <div className="member-actions">
              <label className="button-secondary">
                {busyPosition === key ? "Envoi..." : logoUrls[key] ? "Remplacer" : "Choisir une image"}
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/gif"
                  className="visually-hidden"
                  disabled={busyPosition !== null}
                  onChange={(e) => handleUpload(key, e)}
                />
              </label>
              {logoUrls[key] && (
                <button
                  type="button"
                  className="button-danger"
                  disabled={busyPosition !== null}
                  onClick={() => handleDelete(key)}
                >
                  Retirer
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
      <p className="meta">PNG, JPEG ou GIF, 1 Mo maximum.</p>

      {error && <p className="error">{error}</p>}
    </section>
  );
}
