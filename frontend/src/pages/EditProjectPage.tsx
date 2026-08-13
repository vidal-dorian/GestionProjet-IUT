import { type FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ApiError,
  deleteProject,
  getProject,
  type GithubIssue,
  linkGithubRepo,
  listGithubIssues,
  syncGithubIssues,
  updateProject,
} from "../api/projects";

export default function EditProjectPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [projectName, setProjectName] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [githubRepo, setGithubRepo] = useState("");
  const [linkedRepo, setLinkedRepo] = useState<string | null>(null);
  const [lastSyncedAt, setLastSyncedAt] = useState<string | null>(null);
  const [issues, setIssues] = useState<GithubIssue[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [githubError, setGithubError] = useState<string | null>(null);
  const [linkingGithub, setLinkingGithub] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) return;
    getProject(projectId)
      .then((project) => {
        setProjectName(project.name);
        setName(project.name);
        setDescription(project.description ?? "");
        setGithubRepo(project.github_repo ?? "");
        setLinkedRepo(project.github_repo);
        setLastSyncedAt(project.github_last_synced_at);
        if (project.github_repo) {
          listGithubIssues(projectId).then(setIssues).catch(() => {});
        }
      })
      .catch(() => setError("Ce projet est introuvable."))
      .finally(() => setLoading(false));
  }, [projectId]);

  async function handleLinkGithub(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setGithubError(null);

    if (!githubRepo.trim()) {
      setGithubError("Le dépôt est obligatoire (format owner/repo).");
      return;
    }

    setLinkingGithub(true);
    try {
      const updated = await linkGithubRepo(projectId!, githubRepo.trim());
      setLinkedRepo(updated.github_repo);
      setLastSyncedAt(updated.github_last_synced_at);
      setIssues([]);
    } catch (err) {
      setGithubError(err instanceof ApiError ? err.message : "Impossible de lier ce dépôt pour le moment.");
    } finally {
      setLinkingGithub(false);
    }
  }

  async function handleSync() {
    setSyncError(null);
    setSyncing(true);
    try {
      const result = await syncGithubIssues(projectId!);
      setLastSyncedAt(result.synced_at);
      const fetchedIssues = await listGithubIssues(projectId!);
      setIssues(fetchedIssues);
    } catch (err) {
      setSyncError(err instanceof ApiError ? err.message : "Impossible de synchroniser les issues pour le moment.");
    } finally {
      setSyncing(false);
    }
  }

  async function handleDelete() {
    const confirmed = window.confirm(
      `Supprimer le projet « ${projectName} » ? Cette action est irréversible : tous les membres et toutes les heures saisies seront définitivement supprimés.`,
    );
    if (!confirmed) return;

    setDeleting(true);
    try {
      await deleteProject(projectId!);
      navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible de supprimer ce projet pour le moment.");
      setDeleting(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError("Le nom du projet est obligatoire.");
      return;
    }

    setSubmitting(true);
    try {
      await updateProject(projectId!, {
        name: name.trim(),
        description: description.trim() || undefined,
      });
      navigate(`/projects/${projectId}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible de modifier le projet pour le moment.");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="page">
        <p>Chargement...</p>
      </div>
    );
  }

  return (
    <div className="page">
      <Link to={`/projects/${projectId}`} className="back-link">
        ← Retour au projet
      </Link>
      <h1>Modifier le projet</h1>
      <form onSubmit={handleSubmit} className="form">
        <label htmlFor="name">Nom du projet *</label>
        <input
          id="name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={120}
          required
        />

        <label htmlFor="description">Description</label>
        <textarea
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={4}
        />

        {error && <p className="error">{error}</p>}

        <button type="submit" disabled={submitting}>
          {submitting ? "Enregistrement..." : "Enregistrer"}
        </button>
      </form>

      <section className="chart-section">
        <h2>Intégration GitHub</h2>
        {linkedRepo && (
          <p className="meta">
            Dépôt lié :{" "}
            <a href={`https://github.com/${linkedRepo}`} target="_blank" rel="noreferrer">
              {linkedRepo}
            </a>
          </p>
        )}
        <form onSubmit={handleLinkGithub} className="form form-inline">
          <label htmlFor="github-repo">Dépôt GitHub (owner/repo)</label>
          <input
            id="github-repo"
            type="text"
            value={githubRepo}
            onChange={(e) => setGithubRepo(e.target.value)}
            placeholder="owner/repo"
          />

          {githubError && <p className="error">{githubError}</p>}

          <button type="submit" disabled={linkingGithub}>
            {linkingGithub ? "Vérification..." : linkedRepo ? "Mettre à jour" : "Lier le dépôt"}
          </button>
        </form>

        {linkedRepo && (
          <div className="github-sync">
            <p className="meta">
              {lastSyncedAt
                ? `Dernière synchronisation : ${new Date(lastSyncedAt).toLocaleString()}`
                : "Pas encore synchronisé."}
            </p>
            <button type="button" onClick={handleSync} disabled={syncing}>
              {syncing ? "Synchronisation..." : "Synchroniser les issues"}
            </button>

            {syncError && <p className="error">{syncError}</p>}

            {issues.length > 0 && (
              <ul className="github-issues-list">
                {issues.map((issue) => (
                  <li key={issue.id}>
                    <a href={issue.url} target="_blank" rel="noreferrer">
                      #{issue.number} {issue.title}
                    </a>{" "}
                    <span className={`badge badge-${issue.state}`}>{issue.state}</span>
                    {issue.labels.map((label) => (
                      <span key={label} className="badge">
                        {label}
                      </span>
                    ))}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </section>

      <section className="danger-zone">
        <h2>Zone dangereuse</h2>
        <p className="meta">
          Supprimer ce projet supprime aussi définitivement tous ses membres et toutes les heures saisies.
        </p>
        <button type="button" className="button-danger" onClick={handleDelete} disabled={deleting}>
          {deleting ? "Suppression..." : "Supprimer le projet"}
        </button>
      </section>
    </div>
  );
}
