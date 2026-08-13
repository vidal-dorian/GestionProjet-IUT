import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getProject, type Project } from "../api/projects";
import { listMembers, type Member } from "../api/members";
import { listSprints, type Sprint } from "../api/sprints";
import {
  getHoursByCategory,
  getHoursByIssue,
  getHoursOverTime,
  getProjectStats,
  getRecentEntries,
  getSprintStats,
  type HoursByCategory,
  type HoursByIssue,
  type HoursOverTime,
  type ProjectStats,
  type RecentTimeEntry,
  type SprintStats,
} from "../api/dashboard";
import HoursByCategoryChart from "../components/HoursByCategoryChart";
import HoursByIssueChart from "../components/HoursByIssueChart";
import HoursByMemberChart from "../components/HoursByMemberChart";
import HoursOverTimeChart from "../components/HoursOverTimeChart";
import ProjectStatsTiles from "../components/ProjectStatsTiles";
import RecentEntriesList from "../components/RecentEntriesList";

function formatHours(hours: number): string {
  return `${Math.round(hours * 100) / 100} h`;
}

export default function DashboardPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [members, setMembers] = useState<Member[] | null>(null);
  const [hoursOverTime, setHoursOverTime] = useState<HoursOverTime | null>(null);
  const [recentEntries, setRecentEntries] = useState<RecentTimeEntry[] | null>(null);
  const [stats, setStats] = useState<ProjectStats | null>(null);
  const [hoursByIssue, setHoursByIssue] = useState<HoursByIssue | null>(null);
  const [hoursByCategory, setHoursByCategory] = useState<HoursByCategory | null>(null);
  const [sprints, setSprints] = useState<Sprint[]>([]);
  const [selectedSprintId, setSelectedSprintId] = useState<number | "">("");
  const [sprintStats, setSprintStats] = useState<SprintStats | null>(null);
  const [sprintStatsError, setSprintStatsError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) return;
    Promise.all([
      getProject(projectId),
      listMembers(projectId),
      getHoursOverTime(projectId),
      getRecentEntries(projectId),
      getProjectStats(projectId),
      getHoursByIssue(projectId),
      listSprints(projectId),
      getHoursByCategory(projectId),
    ])
      .then(
        ([
          projectData,
          membersData,
          hoursOverTimeData,
          recentEntriesData,
          statsData,
          hoursByIssueData,
          sprintsData,
          hoursByCategoryData,
        ]) => {
          setProject(projectData);
          setMembers(membersData);
          setHoursOverTime(hoursOverTimeData);
          setRecentEntries(recentEntriesData);
          setStats(statsData);
          setHoursByIssue(hoursByIssueData);
          setSprints(sprintsData);
          setHoursByCategory(hoursByCategoryData);
        },
      )
      .catch(() => setError("Impossible de charger le dashboard pour le moment."));
  }, [projectId]);

  useEffect(() => {
    if (!projectId || selectedSprintId === "") {
      setSprintStats(null);
      return;
    }
    setSprintStatsError(null);
    getSprintStats(projectId, selectedSprintId)
      .then(setSprintStats)
      .catch(() => setSprintStatsError("Impossible de charger le détail de ce sprint pour le moment."));
  }, [projectId, selectedSprintId]);

  if (error) {
    return (
      <div className="page">
        <p className="error">{error}</p>
        <Link to={`/projects/${projectId}`}>Retour au projet</Link>
      </div>
    );
  }

  if (!project || !members || !hoursOverTime || !recentEntries || !stats || !hoursByIssue || !hoursByCategory) {
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
        <h2>Heures par User Story</h2>
        {hoursByIssue.items.length === 0 && hoursByIssue.unattached_hours === 0 ? (
          <p>Aucune heure saisie sur ce projet pour l'instant.</p>
        ) : (
          <HoursByIssueChart data={hoursByIssue} />
        )}
      </section>

      <section className="chart-section">
        <h2>Heures par catégorie</h2>
        {hoursByCategory.items.length === 0 && hoursByCategory.unattached_hours === 0 ? (
          <p>Aucune heure saisie sur ce projet pour l'instant.</p>
        ) : (
          <HoursByCategoryChart data={hoursByCategory} />
        )}
      </section>

      {sprints.length > 0 && (
        <section className="chart-section">
          <h2>Détail par sprint</h2>
          <select value={selectedSprintId} onChange={(e) => setSelectedSprintId(e.target.value ? Number(e.target.value) : "")}>
            <option value="">Sélectionner un sprint...</option>
            {sprints.map((sprint) => (
              <option key={sprint.id} value={sprint.id}>
                {sprint.name}
              </option>
            ))}
          </select>

          {sprintStatsError && <p className="error">{sprintStatsError}</p>}

          {sprintStats && (
            <div className="sprint-stats">
              <p className="meta">Total : {formatHours(sprintStats.total_hours)}</p>

              <h3>Heures par membre</h3>
              {sprintStats.hours_by_member.length === 0 ? (
                <p>Aucune heure saisie sur ce sprint.</p>
              ) : (
                <ul className="member-list">
                  {sprintStats.hours_by_member.map((item) => (
                    <li key={item.member_id}>
                      <span>{item.member_name}</span>
                      <span className="member-hours">{formatHours(item.hours)}</span>
                    </li>
                  ))}
                </ul>
              )}

              <h3>Heures par issue</h3>
              {sprintStats.hours_by_issue.items.length === 0 && sprintStats.hours_by_issue.unattached_hours === 0 ? (
                <p>Aucune heure saisie sur ce sprint.</p>
              ) : (
                <ul className="member-list">
                  {sprintStats.hours_by_issue.items.map((item) => (
                    <li key={item.issue_number}>
                      <a href={item.issue_url} target="_blank" rel="noreferrer">
                        #{item.issue_number} {item.issue_title}
                      </a>
                      <span className="member-hours">{formatHours(item.hours)}</span>
                    </li>
                  ))}
                  {sprintStats.hours_by_issue.unattached_hours > 0 && (
                    <li>
                      <span>Sans issue rattachée</span>
                      <span className="member-hours">{formatHours(sprintStats.hours_by_issue.unattached_hours)}</span>
                    </li>
                  )}
                </ul>
              )}
            </div>
          )}
        </section>
      )}

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
