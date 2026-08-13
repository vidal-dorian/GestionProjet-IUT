import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getProject, type Project } from "../api/projects";
import MembersSection from "../components/MembersSection";

export default function ProjectPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) return;
    getProject(projectId)
      .then(setProject)
      .catch(() => setError("Ce projet est introuvable."));
  }, [projectId]);

  if (error) {
    return (
      <div className="page">
        <p className="error">{error}</p>
        <Link to="/">Retour à l'accueil</Link>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="page">
        <p>Chargement...</p>
      </div>
    );
  }

  return (
    <div className="page">
      <Link to="/" className="back-link">
        ← Retour aux projets
      </Link>
      <h1>{project.name}</h1>
      {project.description && <p className="description">{project.description}</p>}
      <p className="meta">
        Créé le {new Date(project.created_at).toLocaleDateString("fr-FR")}
      </p>

      <MembersSection projectId={project.id} />
    </div>
  );
}
