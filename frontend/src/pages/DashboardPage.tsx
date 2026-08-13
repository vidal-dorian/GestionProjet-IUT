import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getProject, type Project } from "../api/projects";
import { listMembers, type Member } from "../api/members";
import {
  getHoursOverTime,
  getProjectStats,
  getRecentEntries,
  type HoursOverTime,
  type ProjectStats,
  type RecentTimeEntry,
} from "../api/dashboard";
import HoursByMemberChart from "../components/HoursByMemberChart";
import HoursOverTimeChart from "../components/HoursOverTimeChart";
import ProjectStatsTiles from "../components/ProjectStatsTiles";
import RecentEntriesList from "../components/RecentEntriesList";

export default function DashboardPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [members, setMembers] = useState<Member[] | null>(null);
  const [hoursOverTime, setHoursOverTime] = useState<HoursOverTime | null>(null);
  const [recentEntries, setRecentEntries] = useState<RecentTimeEntry[] | null>(null);
  const [stats, setStats] = useState<ProjectStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) return;
    Promise.all([
      getProject(projectId),
      listMembers(projectId),
      getHoursOverTime(projectId),
      getRecentEntries(projectId),
      getProjectStats(projectId),
    ])
      .then(([projectData, membersData, hoursOverTimeData, recentEntriesData, statsData]) => {
        setProject(projectData);
        setMembers(membersData);
        setHoursOverTime(hoursOverTimeData);
        setRecentEntries(recentEntriesData);
        setStats(statsData);
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

  if (!project || !members || !hoursOverTime || !recentEntries || !stats) {
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
        <h2>Indicateurs clés</h2>
        <ProjectStatsTiles stats={stats} />
      </section>

      <section className="chart-section">
        <h2>Heures par membre</h2>
        {members.length === 0 ? (
          <p>Aucun membre sur ce projet pour l'instant.</p>
        ) : (
          <HoursByMemberChart members={members} />
        )}
      </section>

      <section className="chart-section">
        <h2>Évolution des heures</h2>
        {hoursOverTime.points.length === 0 ? (
          <p>Aucune heure saisie sur ce projet pour l'instant.</p>
        ) : (
          <HoursOverTimeChart data={hoursOverTime} />
        )}
      </section>

      <section className="chart-section">
        <h2>Dernières entrées</h2>
        {recentEntries.length === 0 ? (
          <p>Aucune entrée sur ce projet pour l'instant.</p>
        ) : (
          <RecentEntriesList entries={recentEntries} />
        )}
      </section>
    </div>
  );
}
