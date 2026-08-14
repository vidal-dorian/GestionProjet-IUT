import { useEffect } from "react";
import { Link } from "react-router-dom";
import ProjectSwitcher from "./ProjectSwitcher";

export const LAST_PROJECT_STORAGE_KEY = "lastProjectId";

interface ProjectNavProps {
  projectId: number;
  projectName: string;
  active: "home" | "dashboard" | "settings";
  canManage: boolean;
}

export default function ProjectNav({ projectId, projectName, active, canManage }: ProjectNavProps) {
  useEffect(() => {
    localStorage.setItem(LAST_PROJECT_STORAGE_KEY, String(projectId));
  }, [projectId]);

  return (
    <nav className="project-nav">
      <div className="project-nav-inner">
        <div className="project-nav-identity">
          <Link to={`/projects/${projectId}`} className="project-nav-name">
            {projectName}
          </Link>
          <ProjectSwitcher currentProjectId={projectId} />
        </div>

        <div className="project-nav-links">
          <Link to={`/projects/${projectId}`} className={active === "home" ? "project-nav-link is-active" : "project-nav-link"}>
            Saisie
          </Link>
          <Link
            to={`/projects/${projectId}/dashboard`}
            className={active === "dashboard" ? "project-nav-link is-active" : "project-nav-link"}
          >
            Dashboard
          </Link>
          {canManage && (
            <Link
              to={`/projects/${projectId}/settings`}
              className={active === "settings" ? "project-nav-link is-active" : "project-nav-link"}
            >
              Paramètres
            </Link>
          )}
        </div>

        <div className="project-nav-account">
          <Link to="/projects" className="project-nav-browse">
            Tous les projets
          </Link>
          <a href="/cdn-cgi/access/logout" className="project-nav-logout">
            Se déconnecter
          </a>
        </div>
      </div>
    </nav>
  );
}
