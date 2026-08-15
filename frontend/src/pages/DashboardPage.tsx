import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { type Account, me } from "../api/auth";
import { downloadProjectExport, downloadSprintBurndownExport } from "../api/exports";
import ProjectNav from "../components/ProjectNav";
import {
  ApiError,
  getProject,
  listContributors,
  listProjectMembers,
  type Contributor,
  type Project,
  type ProjectMember,
} from "../api/projects";
import { listRoles, type TeamRole } from "../api/roles";
import {
  getSprintBurndown,
  listSprints,
  replaceSprintRoleAssignments,
  type BurndownChartData,
  type Sprint,
  type SprintRoleAssignment,
} from "../api/sprints";
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
import BurndownChart from "../components/BurndownChart";
import GanttChart from "../components/GanttChart";
import HoursByCategoryChart from "../components/HoursByCategoryChart";
import HoursByContributorChart from "../components/HoursByContributorChart";
import HoursByIssueChart from "../components/HoursByIssueChart";
import HoursOverTimeChart from "../components/HoursOverTimeChart";
import ProjectStatsTiles from "../components/ProjectStatsTiles";
import RecentEntriesList from "../components/RecentEntriesList";

function formatHours(hours: number): string {
  return `${Math.round(hours * 100) / 100} h`;
}

export default function DashboardPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [contributors, setContributors] = useState<Contributor[] | null>(null);
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
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [roles, setRoles] = useState<TeamRole[]>([]);
  const [members, setMembers] = useState<ProjectMember[]>([]);
  const [roleAssignments, setRoleAssignments] = useState<SprintRoleAssignment[]>([]);
  const [assignmentError, setAssignmentError] = useState<string | null>(null);
  const [assignmentSaving, setAssignmentSaving] = useState(false);
  const [newRoleId, setNewRoleId] = useState<number | "">("");
  const [newMemberId, setNewMemberId] = useState<number | "">("");
  const [account, setAccount] = useState<Account | null>(null);
  const [burndown, setBurndown] = useState<BurndownChartData | null>(null);
  const [burndownError, setBurndownError] = useState<string | null>(null);
  const [burndownExporting, setBurndownExporting] = useState(false);
  const [burndownExportError, setBurndownExportError] = useState<string | null>(null);

  useEffect(() => {
    me()
      .then(setAccount)
      .catch(() => setAccount(null));
  }, []);

  useEffect(() => {
    if (!projectId) return;
    Promise.all([
      getProject(projectId),
      listContributors(projectId),
      getHoursOverTime(projectId),
      getRecentEntries(projectId),
      getProjectStats(projectId),
      getHoursByIssue(projectId),
      listSprints(projectId),
      getHoursByCategory(projectId),
      listRoles(projectId),
      listProjectMembers(projectId),
    ])
      .then(
        ([
          projectData,
          contributorsData,
          hoursOverTimeData,
          recentEntriesData,
          statsData,
          hoursByIssueData,
          sprintsData,
          hoursByCategoryData,
          rolesData,
          membersData,
        ]) => {
          setProject(projectData);
          setContributors(contributorsData);
          setHoursOverTime(hoursOverTimeData);
          setRecentEntries(recentEntriesData);
          setStats(statsData);
          setHoursByIssue(hoursByIssueData);
          setSprints(sprintsData);
          setHoursByCategory(hoursByCategoryData);
          setRoles(rolesData);
          setMembers(membersData);
        },
      )
      .catch(() => setError("Impossible de charger le dashboard pour le moment."));
  }, [projectId]);

  useEffect(() => {
    if (!projectId || selectedSprintId === "") {
      setSprintStats(null);
      setBurndown(null);
      return;
    }
    setSprintStatsError(null);
    setAssignmentError(null);
    getSprintStats(projectId, selectedSprintId)
      .then((stats) => {
        setSprintStats(stats);
        setRoleAssignments(stats.role_assignments);
      })
      .catch(() => setSprintStatsError("Impossible de charger le détail de ce sprint pour le moment."));

    setBurndownError(null);
    getSprintBurndown(projectId, selectedSprintId)
      .then(setBurndown)
      .catch(() => setBurndownError("Impossible de charger le burndown pour le moment."));
  }, [projectId, selectedSprintId]);

  async function persistAssignments(next: SprintRoleAssignment[]) {
    if (!projectId || selectedSprintId === "") return;
    setAssignmentSaving(true);
    setAssignmentError(null);
    try {
      const saved = await replaceSprintRoleAssignments(
        projectId,
        selectedSprintId,
        next.map((a) => ({ role_id: a.role_id, account_id: a.account_id })),
      );
      setRoleAssignments(saved);
    } catch (err) {
      setAssignmentError(err instanceof ApiError ? err.message : "Impossible d'enregistrer l'assignation.");
    } finally {
      setAssignmentSaving(false);
    }
  }

  function handleAssignRole() {
    if (newRoleId === "" || newMemberId === "") return;
    const already = roleAssignments.some((a) => a.role_id === newRoleId && a.account_id === newMemberId);
    if (already) return;
    const role = roles.find((r) => r.id === newRoleId);
    const member = members.find((m) => m.id === newMemberId);
    if (!role || !member) return;
    const next = [
      ...roleAssignments,
      { role_id: role.id, role_name: role.name, account_id: member.id, account_email: member.email },
    ];
    setRoleAssignments(next);
    void persistAssignments(next);
  }

  function handleRemoveAssignment(roleId: number, accountId: number) {
    const next = roleAssignments.filter((a) => !(a.role_id === roleId && a.account_id === accountId));
    setRoleAssignments(next);
    void persistAssignments(next);
  }

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

  async function handleBurndownExport() {
    if (!projectId || selectedSprintId === "") return;
    setBurndownExportError(null);
    setBurndownExporting(true);
    try {
      await downloadSprintBurndownExport(projectId, selectedSprintId);
    } catch (err) {
      setBurndownExportError(err instanceof ApiError ? err.message : "Impossible d'exporter le burndown pour le moment.");
    } finally {
      setBurndownExporting(false);
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
    <>
      <ProjectNav projectId={project.id} projectName={project.name} active="dashboard" canManage={canManage} />
      <div className="page">
        <div className="page-header">
          <h1>Dashboard</h1>
          <button type="button" className="button-secondary" onClick={handleExport} disabled={exporting}>
            {exporting ? "Export..." : "Exporter le projet (Excel)"}
          </button>
        </div>
        {exportError && <p className="error">{exportError}</p>}

        <section className="chart-section">
          <h2>Indicateurs clés</h2>
          <ProjectStatsTiles stats={stats} />
        </section>

        <section className="chart-section">
          <h2>Planning des sprints</h2>
          <GanttChart sprints={sprints} />
        </section>

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

          {burndownError && <p className="error">{burndownError}</p>}

          {burndown && (
            <div className="sprint-stats">
              <div className="page-header">
                <h3>Burndown</h3>
                <button type="button" className="button-secondary" onClick={handleBurndownExport} disabled={burndownExporting}>
                  {burndownExporting ? "Export..." : "Exporter (Excel)"}
                </button>
              </div>
              {burndownExportError && <p className="error">{burndownExportError}</p>}
              {burndown.matched_issue_count === 0 ? (
                <p>
                  Aucune US GitHub n'est labellisée « {burndown.sprint.name} ». Ajoute ce label aux US
                  correspondantes sur GitHub pour voir apparaître ce burndown.
                </p>
              ) : (
                <>
                  <p className="meta">
                    {burndown.total_points} story point{burndown.total_points > 1 ? "s" : ""} au total sur{" "}
                    {burndown.matched_issue_count} US
                    {burndown.unestimated_issue_count > 0 &&
                      ` (dont ${burndown.unestimated_issue_count} sans valorisation, comptée${
                        burndown.unestimated_issue_count > 1 ? "s" : ""
                      } pour 0)`}
                  </p>
                  <BurndownChart ideal={burndown.ideal} actual={burndown.actual} totalPoints={burndown.total_points} />
                </>
              )}
            </div>
          )}

          {sprintStatsError && <p className="error">{sprintStatsError}</p>}

          {sprintStats && (
            <div className="sprint-stats">
              <p className="meta">Total : {formatHours(sprintStats.total_hours)}</p>

              <h3>Heures par contributeur</h3>
              {sprintStats.hours_by_account.length === 0 ? (
                <p>Aucune heure saisie sur ce sprint.</p>
              ) : (
                <ul className="member-list">
                  {sprintStats.hours_by_account.map((item) => (
                    <li key={item.account_id}>
                      <span>{item.account_email}</span>
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

              <h3>Rôles</h3>
              {roleAssignments.length === 0 ? (
                <p>Aucun rôle assigné sur ce sprint.</p>
              ) : (
                <ul className="member-list">
                  {roleAssignments.map((assignment) => (
                    <li key={`${assignment.role_id}-${assignment.account_id}`}>
                      <span>
                        {assignment.role_name} — {assignment.account_email}
                      </span>
                      <button
                        type="button"
                        className="button-danger"
                        disabled={assignmentSaving}
                        onClick={() => handleRemoveAssignment(assignment.role_id, assignment.account_id)}
                      >
                        Retirer
                      </button>
                    </li>
                  ))}
                </ul>
              )}

              {assignmentError && <p className="error">{assignmentError}</p>}

              {roles.length > 0 && members.length > 0 && (
                <div className="form form-inline">
                  <label htmlFor="assign-role">Rôle</label>
                  <select
                    id="assign-role"
                    value={newRoleId}
                    onChange={(e) => setNewRoleId(e.target.value ? Number(e.target.value) : "")}
                  >
                    <option value="">Sélectionner un rôle...</option>
                    {roles.map((role) => (
                      <option key={role.id} value={role.id}>
                        {role.name}
                      </option>
                    ))}
                  </select>

                  <label htmlFor="assign-member">Membre</label>
                  <select
                    id="assign-member"
                    value={newMemberId}
                    onChange={(e) => setNewMemberId(e.target.value ? Number(e.target.value) : "")}
                  >
                    <option value="">Sélectionner un membre...</option>
                    {members.map((member) => (
                      <option key={member.id} value={member.id}>
                        {member.email}
                      </option>
                    ))}
                  </select>

                  <button
                    type="button"
                    disabled={assignmentSaving || newRoleId === "" || newMemberId === ""}
                    onClick={handleAssignRole}
                  >
                    Assigner
                  </button>
                </div>
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
    </>
  );
}
