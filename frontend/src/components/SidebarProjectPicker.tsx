import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listMyProjects, type ProjectSummary } from "../api/projects";
import { IconChevron, IconGrid } from "./icons";

interface Props {
  currentProjectId?: number;
  currentProjectName?: string;
}

/* En-tête de la sidebar : pastille + nom du projet courant, et bascule vers un
   autre projet quand le compte en a plusieurs. Le `select` natif est superposé
   en transparence plutôt que remplacé par un menu maison — on garde le sélecteur
   système (donc l'accessibilité clavier et la roulette native sur mobile) tout
   en affichant la présentation voulue. */
export default function SidebarProjectPicker({ currentProjectId, currentProjectName }: Props) {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<ProjectSummary[]>([]);

  useEffect(() => {
    listMyProjects()
      .then(setProjects)
      .catch(() => setProjects([]));
  }, []);

  const label = currentProjectName ?? "Mes projets";
  const canSwitch = projects.length > 1;

  return (
    <div className="sidebar-project">
      <span className="sidebar-project-avatar" aria-hidden="true">
        {currentProjectName ? currentProjectName.trim().charAt(0).toUpperCase() : <IconGrid />}
      </span>
      <span className="sidebar-project-text">
        <span className="sidebar-project-name">{label}</span>
        <span className="sidebar-project-hint">{canSwitch ? "Changer de projet" : "Projet"}</span>
      </span>
      {canSwitch && (
        <>
          <IconChevron className="sidebar-project-chevron" />
          <select
            className="sidebar-project-select"
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
        </>
      )}
    </div>
  );
}
