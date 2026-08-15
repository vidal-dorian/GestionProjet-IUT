import { type MouseEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import ProjectNav from "../components/ProjectNav";
import { ApiError, getProject, joinProject, listProjects, type Project, type ProjectSummary } from "../api/projects";
import TimeEntriesSection from "../components/TimeEntriesSection";
import { useAuth } from "../context/AuthContext";

function membershipLabel(status: ProjectSummary["membership_status"]): string | null {
  if (status === "pending") return "Demande en attente";
  if (status === "rejected") return "Demande refusée";
  return null;
}

export default function ProjectHomePage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [summary, setSummary] = useState<ProjectSummary | null>(null);
  const { account, loading: accountLoading } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [joining, setJoining] = useState(false);
  const [joinError, setJoinError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) return;
    getProject(projectId)
      .then(setProject)
      .catch(() => setError("Ce projet est introuvable."));
    listProjects()
      .then((all) => setSummary(all.find((p) => p.id === Number(projectId)) ?? null))
      .catch(() => setSummary(null));
  }, [projectId]);

  async function handleJoin(event: MouseEvent) {
    event.preventDefault();
    if (!projectId) return;
    setJoining(true);
    setJoinError(null);
    try {
      const membership = await joinProject(projectId);
      setSummary((current) =>
        current ? { ...current, is_member: membership.status === "approved", membership_status: membership.status } : current,
      );
    } catch (err) {
      setJoinError(err instanceof ApiError ? err.message : "Impossible de rejoindre ce projet pour le moment.");
    } finally {
      setJoining(false);
    }
  }

  if (error) {
    return (
      <div className="page">
        <p className="error">{error}</p>
        <Link to="/">← Retour à l'accueil</Link>
      </div>
    );
  }

  if (!project || !summary || accountLoading || !account) {
    return (
      <div className="page">
        <p>Chargement...</p>
      </div>
    );
  }

  const canManage = account.is_admin || project.created_by_account_id === account.id;

  if (!summary.is_member) {
    const label = membershipLabel(summary.membership_status);
    const canRequestJoin = summary.membership_status !== "pending";
    return (
      <div className="page">
        <Link to="/projects" className="back-link">
          ← Tous les projets
        </Link>
        <h1>{project.name}</h1>
        {project.description && <p className="description">{project.description}</p>}
        {label && <p className="meta">{label}</p>}
        {joinError && <p className="error">{joinError}</p>}
        {canRequestJoin && (
          <button type="button" className="button-link" onClick={handleJoin} disabled={joining}>
            {joining ? "Envoi..." : summary.membership_status === "rejected" ? "Redemander l'accès" : "Rejoindre ce projet"}
          </button>
        )}
      </div>
    );
  }

  return (
    <>
      <ProjectNav projectId={project.id} projectName={project.name} active="home" canManage={canManage} />
      <div className="page">
        <h1>Bonjour, {account.email.split("@")[0]}</h1>
        {project.description && <p className="description">{project.description}</p>}

        <TimeEntriesSection projectId={project.id} />
      </div>
    </>
  );
}
