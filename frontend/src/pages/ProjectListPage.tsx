import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listProjects, type ProjectSummary } from "../api/projects";

export default function ProjectListPage() {
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listProjects()
      .then(setProjects)
      .catch(() => setError("Impossible de charger les projets pour le moment."));
  }, []);

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
            <li key={project.id}>
              <Link to={`/projects/${project.id}`} className="project-card">
                <h2>{project.name}</h2>
                {project.description && <p className="description">{project.description}</p>}
                <p className="meta">
                  {project.contributor_count} contributeur{project.contributor_count > 1 ? "s" : ""}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
