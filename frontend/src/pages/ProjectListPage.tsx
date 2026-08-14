import { type MouseEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, joinProject, listProjects, type ProjectSummary } from "../api/projects";

export default function ProjectListPage() {
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [joiningId, setJoiningId] = useState<number | null>(null);

  useEffect(() => {
    listProjects()
      .then(setProjects)
      .catch(() => setError("Impossible de charger les projets pour le moment."));
  }, []);

  async function handleJoin(projectId: number, event: MouseEvent) {
    event.preventDefault();
    setJoiningId(projectId);
    try {
      await joinProject(projectId);
      setProjects((current) =>
        current?.map((p) => (p.id === projectId ? { ...p, is_member: true } : p)) ?? current,
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible de rejoindre ce projet pour le moment.");
    } finally {
      setJoiningId(null);
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Projets</h1>
        <Link to="/projects/new" className="button-link">
          Nouveau projet
        </Link>
      </div>

      {error && <p className="error">{error}</p>}

      {projects && projects.length === 0 && (
        <p>
          Aucun projet pour le moment. <Link to="/projects/new">Créez-en un</Link> pour commencer.
        </p>
      )}

      {projects && projects.length > 0 && (
        <ul className="project-list">
          {projects.map((project) => (
            <li key={project.id} className="project-card-item">
              <Link to={`/projects/${project.id}`} className="project-card">
                <div className="project-card-header">
                  <h2>{project.name}</h2>
                  {project.is_member && <span className="badge badge-member">Membre</span>}
                </div>
                {project.description && <p className="description">{project.description}</p>}
                <p className="meta">
                  {project.contributor_count} contributeur{project.contributor_count > 1 ? "s" : ""}
                </p>
              </Link>
              {!project.is_member && (
                <button
                  type="button"
                  className="button-secondary project-card-join"
                  disabled={joiningId === project.id}
                  onClick={(event) => handleJoin(project.id, event)}
                >
                  {joiningId === project.id ? "Adhésion..." : "Rejoindre"}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
