import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { LAST_PROJECT_STORAGE_KEY } from "../components/AppShell";
import { listMyProjects } from "../api/projects";
import ProjectListPage from "./ProjectListPage";

type Resolution = { status: "loading" } | { status: "browse" } | { status: "redirect"; projectId: number };

export default function HomePage() {
  const [resolution, setResolution] = useState<Resolution>({ status: "loading" });

  useEffect(() => {
    listMyProjects()
      .then((projects) => {
        if (projects.length === 0) {
          setResolution({ status: "browse" });
          return;
        }
        const lastId = Number(localStorage.getItem(LAST_PROJECT_STORAGE_KEY));
        const target = projects.find((p) => p.id === lastId) ?? projects[0];
        setResolution({ status: "redirect", projectId: target.id });
      })
      .catch(() => setResolution({ status: "browse" }));
  }, []);

  if (resolution.status === "loading") {
    return (
      <div className="page">
        <p>Chargement...</p>
      </div>
    );
  }

  if (resolution.status === "redirect") {
    return <Navigate to={`/projects/${resolution.projectId}`} replace />;
  }

  return <ProjectListPage />;
}
