import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listMyProjects, type ProjectSummary } from "../api/projects";

interface ProjectSwitcherProps {
  currentProjectId?: number;
}

export default function ProjectSwitcher({ currentProjectId }: ProjectSwitcherProps) {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<ProjectSummary[]>([]);

  useEffect(() => {
    listMyProjects()
      .then(setProjects)
      .catch(() => setProjects([]));
  }, []);

  if (projects.length < 2) {
    return null;
  }

  return (
    <select
      className="project-switcher"
      aria-label="Changer de projet"
      value={currentProjectId ?? ""}
      onChange={(event) => navigate(`/projects/${event.target.value}`)}
    >
      {!currentProjectId && (
        <option value="" disabled>
          Mes projets…
        </option>
      )}
      {projects.map((project) => (
        <option key={project.id} value={project.id}>
          {project.name}
        </option>
      ))}
    </select>
  );
}
