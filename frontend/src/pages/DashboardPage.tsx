import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { downloadProjectExport } from "../api/exports";
import { useAuth } from "../context/AuthContext";
import AppShell from "../components/AppShell";
import PageHeader from "../components/PageHeader";
import { ApiError, getProject, listContributors, type Contributor, type Project } from "../api/projects";
import {
  getHoursByCategory,
  getHoursByIssue,
  getHoursOverTime,
  getProjectStats,
  getRecentEntries,
  type HoursByCategory,
  type HoursByIssue,
  type HoursOverTime,
  type ProjectStats,
  type RecentTimeEntry,
} from "../api/dashboard";
import HoursByCategoryChart from "../components/HoursByCategoryChart";
import HoursByContributorChart from "../components/HoursByContributorChart";
import HoursByIssueChart from "../components/HoursByIssueChart";
import HoursOverTimeChart from "../components/HoursOverTimeChart";
import ProjectStatsTiles from "../components/ProjectStatsTiles";
import RecentEntriesList from "../components/RecentEntriesList";

export default function DashboardPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { account } = useAuth();
  const [project, setProject] = useState<Project | null>(null);
  const [contributors, setContributors] = useState<Contributor[] | null>(null);
  const [hoursOverTime, setHoursOverTime] = useState<HoursOverTime | null>(null);
  const [recentEntries, setRecentEntries] = useState<RecentTimeEntry[] | null>(null);
  const [stats, setStats] = useState<ProjectStats | null>(null);
  const [hoursByIssue, setHoursByIssue] = useState<HoursByIssue | null>(null);
  const [hoursByCategory, setHoursByCategory] = useState<HoursByCategory | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) return;
    Promise.all([
      getProject(projectId),
      listContributors(projectId),
      getHoursOverTime(projectId),
      getRecentEntries(projectId),
      getProjectStats(projectId),
      getHoursByIssue(projectId),
      getHoursByCategory(projectId),
    ])
      .then(
        ([
          projectData,
          contributorsData,
          hoursOverTimeData,
          recentEntriesData,
          statsData,
          hoursByIssueData,
          hoursByCategoryData,
        ]) => {
          setProject(projectData);
          setContributors(contributorsData);
          setHoursOverTime(hoursOverTimeData);
          setRecentEntries(recentEntriesData);
          setStats(statsData);
          setHoursByIssue(hoursByIssueData);
          setHoursByCategory(hoursByCategoryData);
        },
      )
      .catch(() => setError("Impossible de charger le dashboard pour le moment."));
  }, [projectId]);

  async function handleExport() {
    if (!projectId) return;
    setExportError(null);
    setExporting(true);
    try {
      await downloadProjectExport(projectId);
    } catch (err) {
      setExportError(err instanceof ApiError ? err.message : "Impossible d'exporter le projet pour le moment.");
    } finally {
      setExporting(false);
    }
  }

  if (error) {
    return (
      <div className="page">
        <p className="error">{error}</p>
        <Link to={`/projects/${projectId}`}>Retour au projet</Link>
      </div>
    );
  }

  if (!project || !contributors || !hoursOverTime || !recentEntries || !stats || !hoursByIssue || !hoursByCategory) {
    return (
      <div className="page">
        <p>Chargement...</p>
      </div>
    );
  }

  const canManage = !!account && (account.is_admin || project.created_by_account_id === account.id);

  return (
    <AppShell title="Dashboard" project={{ id: project.id, name: project.name }} canManage={canManage}>
      <div className="page page-wide">
        <PageHeader
          title="Dashboard"
          subtitle="Vue d'ensemble de l'activité du projet."
          actions={
            <button type="button" className="button-secondary" onClick={handleExport} disabled={exporting}>
              {exporting ? "Export..." : "Exporter (Excel)"}
            </button>
          }
        />
        {exportError && <p className="error">{exportError}</p>}

        <ProjectStatsTiles stats={stats} />

        <div className="chart-grid">
          <section className="chart-section">
            <h2>Heures par contributeur</h2>
            {contributors.length === 0 ? (
              <p>Aucune heure saisie sur ce projet pour l'instant.</p>
            ) : (
              <HoursByContributorChart contributors={contributors} />
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
        </div>

        <section className="chart-section">
          <h2>Dernières entrées</h2>
          {recentEntries.length === 0 ? (
            <p>Aucune entrée sur ce projet pour l'instant.</p>
          ) : (
            <RecentEntriesList entries={recentEntries} />
          )}
        </section>
      </div>
    </AppShell>
  );
}
