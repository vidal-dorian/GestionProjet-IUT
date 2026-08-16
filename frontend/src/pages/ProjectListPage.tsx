import { type MouseEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import AppShell, { LAST_PROJECT_STORAGE_KEY } from "../components/AppShell";
import PageHeader from "../components/PageHeader";
import { useAuth } from "../context/AuthContext";
import { ApiError, joinProject, listProjects, type ProjectSummary } from "../api/projects";

function membershipLabel(project: ProjectSummary): string | null {
  if (project.membership_status === "pending") return "Demande en attente";
  if (project.membership_status === "rejected") return "Demande refusée";
  return null;
}

export default function ProjectListPage() {
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [joiningId, setJoiningId] = useState<number | null>(null);
  const { isAdmin } = useAuth();

  useEffect(() => {
    listProjects()
      .then(setProjects)
      .catch(() => setError("Impossible de charger les projets pour le moment."));
  }, []);

  async function handleJoin(projectId: number, event: MouseEvent) {
    event.preventDefault();
    setJoiningId(projectId);
    try {
      const membership = await joinProject(projectId);
      setProjects((current) =>
        current?.map((p) =>
          p.id === projectId
            ? { ...p, is_member: membership.status === "approved", membership_status: membership.status }
            : p,
        ) ?? current,
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible de rejoindre ce projet pour le moment.");
    } finally {
      setJoiningId(null);
    }
  }

  const lastProjectId = localStorage.getItem(LAST_PROJECT_STORAGE_KEY);
  const canReturnToLastProject = lastProjectId && projects?.some((p) => p.id === Number(lastProjectId) && p.is_member);

  return (
    <AppShell title="Tous les projets">
    <div className="page page-wide">
      {canReturnToLastProject && (
        <Link to={`/projects/${lastProjectId}`} className="back-link">
          ← Retour à mon espace
        </Link>
      )}
      <PageHeader
        title="Tous les projets"
        subtitle="Rejoignez un projet existant ou créez le vôtre."
        actions={
          <>
            {isAdmin && (
              <Link to="/admin/demandes" className="button-secondary">
                Demandes d'adhésion
              </Link>
            )}
            <Link to="/projects/new" className="button-link">
              Nouveau projet
            </Link>
          </>
        }
      />

      {error && <p className="error">{error}</p>}

      {projects && projects.length === 0 && (
        <p>
          Aucun projet pour le moment. <Link to="/projects/new">Créez-en un</Link> pour commencer.
        </p>
      )}

      {projects && projects.length > 0 && (
        <ul className="project-list">
          {projects.map((project) => {
            const label = membershipLabel(project);
            const canRequestJoin = !project.is_member && project.membership_status !== "pending";
            return (
              <li key={project.id} className="project-card-item">
                <Link to={`/projects/${project.id}`} className="project-card">
                  <div className="project-card-header">
                    <h2>{project.name}</h2>
                    {project.is_member && <span className="badge badge-member">Membre</span>}
                    {label && (
                      <span
                        className={`badge ${project.membership_status === "rejected" ? "badge-rejected" : "badge-pending"}`}
                      >
                        {label}
                      </span>
                    )}
                  </div>
                  {project.description && <p className="description">{project.description}</p>}
                  <p className="meta">
                    {project.contributor_count} contributeur{project.contributor_count > 1 ? "s" : ""}
                  </p>
                </Link>
                {canRequestJoin && (
                  <button
                    type="button"
                    className="button-secondary project-card-join"
                    disabled={joiningId === project.id}
                    onClick={(event) => handleJoin(project.id, event)}
                  >
                    {joiningId === project.id
                      ? "Envoi..."
                      : project.membership_status === "rejected"
                        ? "Redemander l'accès"
                        : "Rejoindre"}
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
    </AppShell>
  );
}
