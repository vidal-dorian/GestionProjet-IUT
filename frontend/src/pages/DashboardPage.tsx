import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getProject, type Project } from "../api/projects";
import { listMembers, type Member } from "../api/members";
import HoursByMemberChart from "../components/HoursByMemberChart";

export default function DashboardPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [members, setMembers] = useState<Member[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) return;
    Promise.all([getProject(projectId), listMembers(projectId)])
      .then(([projectData, membersData]) => {
        setProject(projectData);
        setMembers(membersData);
      })
      .catch(() => setError("Impossible de charger le dashboard pour le moment."));
  }, [projectId]);

  if (error) {
    return (
      <div className="page">
        <p className="error">{error}</p>
        <Link to={`/projects/${projectId}`}>Retour au projet</Link>
      </div>
    );
  }

  if (!project || !members) {
    return (
      <div className="page">
        <p>Chargement...</p>
      </div>
    );
  }

  return (
    <div className="page">
      <Link to={`/projects/${projectId}`} className="back-link">
        ← Retour au projet
      </Link>
      <h1>Dashboard — {project.name}</h1>

      <section className="chart-section">
        <h2>Heures par membre</h2>
        {members.length === 0 ? (
          <p>Aucun membre sur ce projet pour l'instant.</p>
        ) : (
          <HoursByMemberChart members={members} />
        )}
      </section>
    </div>
  );
}
