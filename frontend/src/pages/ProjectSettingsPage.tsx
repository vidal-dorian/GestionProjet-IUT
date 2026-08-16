import { type FormEvent, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { type Account } from "../api/auth";
import { listProjectMembers, removeProjectMember } from "../api/admin";
import { useAuth } from "../context/AuthContext";
import {
  ApiError,
  deleteProject,
  getProject,
  type GithubIssue,
  linkGithubRepo,
  listGithubIssues,
  setGithubLabelFilter,
  syncGithubIssues,
  updateProject,
} from "../api/projects";
import AppShell from "../components/AppShell";
import CategoriesSection from "../components/CategoriesSection";
import PageHeader from "../components/PageHeader";
import RolesSection from "../components/RolesSection";
import SprintsSection from "../components/SprintsSection";

const SETTINGS_SECTIONS = [
  { key: "general", label: "Général" },
  { key: "members", label: "Membres" },
  { key: "github", label: "GitHub" },
  { key: "sprints", label: "Sprints" },
  { key: "categories", label: "Catégories" },
  { key: "roles", label: "Rôles" },
  { key: "danger", label: "Zone dangereuse" },
] as const;

type SettingsSection = (typeof SETTINGS_SECTIONS)[number]["key"];

export default function ProjectSettingsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [projectName, setProjectName] = useState("");
  const [createdByAccountId, setCreatedByAccountId] = useState<number | null>(null);
  const { account } = useAuth();
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
  const [labelFilterInput, setLabelFilterInput] = useState("");
  const [savingLabelFilter, setSavingLabelFilter] = useState(false);
  const [labelFilterError, setLabelFilterError] = useState<string | null>(null);
  const [members, setMembers] = useState<Account[] | null>(null);
  const [removingId, setRemovingId] = useState<number | null>(null);
  const [membersError, setMembersError] = useState<string | null>(null);
  const [section, setSection] = useState<SettingsSection>("general");

  const canManage =
    !!account && (account.is_admin || (createdByAccountId !== null && createdByAccountId === account.id));

  useEffect(() => {
    if (!projectId) return;
    getProject(projectId)
      .then((project) => {
        setProjectName(project.name);
        setCreatedByAccountId(project.created_by_account_id);
        setName(project.name);
        setDescription(project.description ?? "");
        setGithubRepo(project.github_repo ?? "");
        setLinkedRepo(project.github_repo);
        setLastSyncedAt(project.github_last_synced_at);
        setLabelFilterInput(project.github_label_filter.join(", "));
        if (project.github_repo) {
          listGithubIssues(projectId).then(setIssues).catch(() => {});
        }
      })
      .catch(() => setError("Ce projet est introuvable."))
      .finally(() => setLoading(false));
  }, [projectId]);

  useEffect(() => {
    if (!projectId || !canManage) return;
    listProjectMembers(projectId)
      .then(setMembers)
      .catch(() => setMembersError("Impossible de charger les membres pour le moment."));
  }, [projectId, canManage]);

  async function handleRemoveMember(accountId: number) {
    if (!projectId) return;
    setRemovingId(accountId);
    try {
      await removeProjectMember(projectId, accountId);
      setMembers((current) => current?.filter((m) => m.id !== accountId) ?? current);
    } catch {
      setMembersError("Impossible de retirer ce membre pour le moment.");
    } finally {
      setRemovingId(null);
    }
  }

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

  async function handleLabelFilterSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLabelFilterError(null);
    setSavingLabelFilter(true);
    try {
      const labels = labelFilterInput
        .split(",")
        .map((label) => label.trim())
        .filter(Boolean);
      const updated = await setGithubLabelFilter(projectId!, labels);
      setLabelFilterInput(updated.github_label_filter.join(", "));
      const fetchedIssues = await listGithubIssues(projectId!);
      setIssues(fetchedIssues);
    } catch (err) {
      setLabelFilterError(err instanceof ApiError ? err.message : "Impossible d'enregistrer ce filtre.");
    } finally {
      setSavingLabelFilter(false);
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
      navigate("/projects");
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
      const updated = await updateProject(projectId!, {
        name: name.trim(),
        description: description.trim() || undefined,
      });
      setProjectName(updated.name);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible de modifier le projet pour le moment.");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading || !projectId) {
    return (
      <div className="page">
        <p>Chargement...</p>
      </div>
    );
  }

  return (
    <AppShell
      title="Paramètres"
      project={{ id: Number(projectId), name: projectName }}
      canManage={canManage}
    >
      <div className="page page-wide">
        <PageHeader title="Paramètres du projet" subtitle="Configuration, équipe et intégrations." />

        {canManage ? (
          <div className="settings-layout">
            {/* Sous-navigation : verticale à côté du contenu sur grand écran, ruban
                défilant au-dessus sur mobile — une seule section à la fois plutôt
                qu'un défilement de sept blocs empilés. */}
            <nav className="settings-nav" aria-label="Sections des paramètres">
              {SETTINGS_SECTIONS.map((item) => (
                <button
                  key={item.key}
                  type="button"
                  aria-current={section === item.key}
                  className={section === item.key ? "settings-nav-item is-active" : "settings-nav-item"}
                  onClick={() => setSection(item.key)}
                >
                  {item.label}
                </button>
              ))}
            </nav>

            <div className="settings-panel">
              {section === "general" && (
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
              <textarea id="description" value={description} onChange={(e) => setDescription(e.target.value)} rows={4} />

              {error && <p className="error">{error}</p>}

              <button type="submit" disabled={submitting}>
                {submitting ? "Enregistrement..." : "Enregistrer"}
              </button>
            </form>
              )}

              {section === "members" && (
            <section className="member-management">
              <h2>Membres du projet</h2>
              {membersError && <p className="error">{membersError}</p>}
              {members === null && <p>Chargement...</p>}
              {members && members.length === 0 && <p>Aucun membre approuvé pour l'instant.</p>}
              {members && members.length > 0 && (
                <ul className="member-list">
                  {members.map((member) => (
                    <li key={member.id}>
                      <div>
                        <strong>{member.email}</strong>
                        {member.is_admin && <span className="badge">Administrateur</span>}
                      </div>
                      <button
                        type="button"
                        className="button-danger"
                        disabled={removingId === member.id}
                        onClick={() => handleRemoveMember(member.id)}
                      >
                        Retirer
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </section>
              )}

              {section === "github" && (
            <section className="chart-section">
              <h2>Intégration GitHub</h2>
              <p className="meta">
                Pour le burndown : chaque US doit porter un label reprenant exactement le nom du sprint (ex.
                « Sprint 1 ») et être valorisée en story points via le champ « Valorisation » du GitHub Project
                auquel elle appartient.
              </p>
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

                  <form onSubmit={handleLabelFilterSubmit} className="form form-inline">
                    <label htmlFor="github-label-filter">Filtrer par labels (séparés par des virgules)</label>
                    <input
                      id="github-label-filter"
                      type="text"
                      value={labelFilterInput}
                      onChange={(e) => setLabelFilterInput(e.target.value)}
                      placeholder="user-story, epic-7"
                    />
                    <p className="meta">Sans filtre, seules les issues ouvertes sont affichées.</p>

                    {labelFilterError && <p className="error">{labelFilterError}</p>}

                    <button type="submit" disabled={savingLabelFilter}>
                      {savingLabelFilter ? "Enregistrement..." : "Appliquer le filtre"}
                    </button>
                  </form>

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
              )}

              {section === "sprints" && <SprintsSection projectId={Number(projectId)} />}
              {section === "categories" && <CategoriesSection projectId={Number(projectId)} />}
              {section === "roles" && <RolesSection projectId={Number(projectId)} />}

              {section === "danger" && (
                <section className="danger-zone">
                  <h2>Zone dangereuse</h2>
                  <p className="meta">
                    Supprimer ce projet supprime aussi définitivement tous ses membres et toutes les heures saisies.
                  </p>
                  <button type="button" className="button-danger" onClick={handleDelete} disabled={deleting}>
                    {deleting ? "Suppression..." : "Supprimer le projet"}
                  </button>
                </section>
              )}
            </div>
          </div>
        ) : (
          <p className="meta">Réservé au créateur du projet et aux administrateurs.</p>
        )}
      </div>
    </AppShell>
  );
}
