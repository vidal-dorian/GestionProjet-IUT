import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { downloadSprintBurndownExport } from "../api/exports";
import { useAuth } from "../context/AuthContext";
import AppShell from "../components/AppShell";
import PageHeader from "../components/PageHeader";
import { ApiError, getProject, listProjectMembers, type Project, type ProjectMember } from "../api/projects";
import { listRoles, type TeamRole } from "../api/roles";
import {
  getSprintBurndown,
  listSprints,
  replaceSprintRoleAssignments,
  type BurndownChartData,
  type Sprint,
  type SprintRoleAssignment,
} from "../api/sprints";
import { getSprintStats, type SprintStats } from "../api/dashboard";
import BurndownChart from "../components/BurndownChart";
import GanttChart from "../components/GanttChart";

function formatHours(hours: number): string {
  return `${Math.round(hours * 100) / 100} h`;
}

function formatDate(isoDate: string): string {
  return new Date(`${isoDate}T00:00:00`).toLocaleDateString("fr-FR", { day: "2-digit", month: "short" });
}

function byStartDate(sprints: Sprint[]): Sprint[] {
  return [...sprints].sort((a, b) => a.start_date.localeCompare(b.start_date));
}

/* Sprint ouvert par défaut : celui en cours, sinon le dernier démarré, sinon le
   premier à venir. Ouvrir la page sur un état vide obligerait à choisir avant
   de voir quoi que ce soit. */
function defaultSprint(sprints: Sprint[]): Sprint | undefined {
  const ordered = byStartDate(sprints);
  const today = new Date().toISOString().slice(0, 10);
  return (
    ordered.find((sprint) => sprint.start_date <= today && today <= sprint.end_date) ??
    [...ordered].reverse().find((sprint) => sprint.start_date <= today) ??
    ordered[0]
  );
}

export default function SprintsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { account } = useAuth();
  const [project, setProject] = useState<Project | null>(null);
  const [sprints, setSprints] = useState<Sprint[] | null>(null);
  const [selectedSprintId, setSelectedSprintId] = useState<number | "">("");
  const [sprintStats, setSprintStats] = useState<SprintStats | null>(null);
  const [sprintStatsError, setSprintStatsError] = useState<string | null>(null);
  const [burndown, setBurndown] = useState<BurndownChartData | null>(null);
  const [burndownError, setBurndownError] = useState<string | null>(null);
  const [burndownExporting, setBurndownExporting] = useState(false);
  const [burndownExportError, setBurndownExportError] = useState<string | null>(null);
  const [roles, setRoles] = useState<TeamRole[]>([]);
  const [members, setMembers] = useState<ProjectMember[]>([]);
  const [roleAssignments, setRoleAssignments] = useState<SprintRoleAssignment[]>([]);
  const [assignmentError, setAssignmentError] = useState<string | null>(null);
  const [assignmentSaving, setAssignmentSaving] = useState(false);
  const [newRoleId, setNewRoleId] = useState<number | "">("");
  const [newMemberId, setNewMemberId] = useState<number | "">("");
  const [error, setError] = useState<string | null>(null);
  const tabsRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!projectId) return;
    Promise.all([getProject(projectId), listSprints(projectId), listRoles(projectId), listProjectMembers(projectId)])
      .then(([projectData, sprintsData, rolesData, membersData]) => {
        setProject(projectData);
        setSprints(sprintsData);
        setRoles(rolesData);
        setMembers(membersData);
        const current = defaultSprint(sprintsData);
        if (current) setSelectedSprintId(current.id);
      })
      .catch(() => setError("Impossible de charger les sprints pour le moment."));
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

  // Le ruban défile horizontalement sur petit écran : sans ça, le sprint
  // sélectionné par défaut peut se retrouver hors du champ de vision.
  useEffect(() => {
    const active = tabsRef.current?.querySelector<HTMLElement>(".sprint-tab.is-active");
    active?.scrollIntoView({ inline: "center", block: "nearest" });
  }, [selectedSprintId]);

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

  if (!project || !sprints) {
    return (
      <div className="page">
        <p>Chargement...</p>
      </div>
    );
  }

  const canManage = !!account && (account.is_admin || project.created_by_account_id === account.id);
  const orderedSprints = byStartDate(sprints);
  const selectedSprint = sprints.find((sprint) => sprint.id === selectedSprintId) ?? null;

  return (
    <AppShell title="Sprints" project={{ id: project.id, name: project.name }} canManage={canManage}>
      <div className="page page-wide">
        <PageHeader
          title="Sprints"
          subtitle="Planning de l'itération, avancement en story points et rôles de l'équipe."
          actions={
            selectedSprint && (
              <button type="button" className="button-secondary" onClick={handleBurndownExport} disabled={burndownExporting}>
                {burndownExporting ? "Export..." : "Exporter le burndown"}
              </button>
            )
          }
        />
        {burndownExportError && <p className="error">{burndownExportError}</p>}

        {sprints.length === 0 ? (
          <section className="chart-section">
            <h2>Aucun sprint</h2>
            <p>
              Les sprints se créent depuis les paramètres du projet. Ils servent ensuite de base au planning, au
              burndown et à l'attribution des rôles.
            </p>
            {canManage && (
              <Link to={`/projects/${project.id}/settings`} className="button-link">
                Créer un sprint
              </Link>
            )}
          </section>
        ) : (
          <>
            <section className="chart-section">
              <h2>Planning</h2>
              <GanttChart sprints={orderedSprints} />
            </section>

            {/* Sélecteur en rubans plutôt qu'en liste déroulante : les sprints sont
                peu nombreux et on veut voir d'un coup lequel est ouvert. */}
            <div className="sprint-tabs" role="tablist" aria-label="Choisir un sprint" ref={tabsRef}>
              {orderedSprints.map((sprint) => (
                <button
                  key={sprint.id}
                  type="button"
                  role="tab"
                  aria-selected={sprint.id === selectedSprintId}
                  className={sprint.id === selectedSprintId ? "sprint-tab is-active" : "sprint-tab"}
                  onClick={() => setSelectedSprintId(sprint.id)}
                >
                  <span className="sprint-tab-name">{sprint.name}</span>
                  <span className="sprint-tab-dates">
                    {formatDate(sprint.start_date)} → {formatDate(sprint.end_date)}
                  </span>
                </button>
              ))}
            </div>

            {burndownError && <p className="error">{burndownError}</p>}
            {sprintStatsError && <p className="error">{sprintStatsError}</p>}

            {burndown && (
              <section className="chart-section">
                <h2>Burndown</h2>
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
              </section>
            )}

            {sprintStats && (
              <>
                <div className="chart-grid">
                  <section className="chart-section">
                    <h2>Heures par contributeur</h2>
                    <p className="meta">Total : {formatHours(sprintStats.total_hours)}</p>
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
                  </section>

                  <section className="chart-section">
                    <h2>Heures par User Story</h2>
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
                            <span className="member-hours">
                              {formatHours(sprintStats.hours_by_issue.unattached_hours)}
                            </span>
                          </li>
                        )}
                      </ul>
                    )}
                  </section>
                </div>

                <section className="chart-section">
                  <h2>Rôles sur ce sprint</h2>
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
                </section>
              </>
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}
