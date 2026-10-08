import { type FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ApiError, getProject, type Project } from "../api/projects";
import {
  createReport,
  listReports,
  REPORT_TYPE_LABELS,
  type ReportSummary,
  type ReportType,
} from "../api/reports";
import { listSprints, type Sprint } from "../api/sprints";
import AppShell from "../components/AppShell";
import PageHeader from "../components/PageHeader";
import { useAuth } from "../context/AuthContext";

const REPORT_TYPES = Object.keys(REPORT_TYPE_LABELS) as ReportType[];

function todayIso(): string {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

function formatDate(isoDate: string): string {
  return new Date(`${isoDate}T00:00:00`).toLocaleDateString("fr-FR", {
    weekday: "short",
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

/* Sprint proposé par défaut : celui qui contient la date choisie, sinon le
   dernier démarré avant elle. */
function sprintForDate(sprints: Sprint[], isoDate: string): Sprint | undefined {
  const ordered = [...sprints].sort((a, b) => a.start_date.localeCompare(b.start_date));
  return (
    ordered.find((sprint) => sprint.start_date <= isoDate && isoDate <= sprint.end_date) ??
    [...ordered].reverse().find((sprint) => sprint.start_date <= isoDate) ??
    ordered[0]
  );
}

export default function ReportsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { account } = useAuth();
  const [project, setProject] = useState<Project | null>(null);
  const [sprints, setSprints] = useState<Sprint[]>([]);
  const [reports, setReports] = useState<ReportSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<ReportType | "all">("all");
  const [newType, setNewType] = useState<ReportType>("daily");
  const [newDate, setNewDate] = useState(todayIso());
  const [newSprintId, setNewSprintId] = useState<number | "">("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) return;
    Promise.all([getProject(projectId), listSprints(projectId), listReports(projectId)])
      .then(([projectData, sprintData, reportData]) => {
        setProject(projectData);
        setSprints(sprintData);
        setReports(reportData);
        const current = sprintForDate(sprintData, todayIso());
        if (current) setNewSprintId(current.id);
      })
      .catch(() => setError("Impossible de charger les comptes-rendus pour le moment."));
  }, [projectId]);

  const todayDaily = useMemo(
    () => reports?.find((report) => report.type === "daily" && report.meeting_date === todayIso()),
    [reports],
  );

  async function create(type: ReportType, meetingDate: string, sprintId: number | null) {
    if (!projectId) return;
    setCreating(true);
    setCreateError(null);
    try {
      const report = await createReport(projectId, { type, sprint_id: sprintId, meeting_date: meetingDate });
      navigate(`/projects/${projectId}/reports/${report.id}`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409 && type === "daily") {
        // Quelqu'un vient de le créer : on rejoint le sien plutôt que d'en refaire un.
        const latest = await listReports(projectId).catch(() => []);
        const existing = latest.find((r) => r.type === "daily" && r.meeting_date === meetingDate);
        if (existing) {
          navigate(`/projects/${projectId}/reports/${existing.id}`);
          return;
        }
      }
      setCreateError(err instanceof ApiError ? err.message : "Impossible de créer ce compte-rendu pour le moment.");
    } finally {
      setCreating(false);
    }
  }

  function handleTodayDaily() {
    if (todayDaily) {
      navigate(`/projects/${projectId}/reports/${todayDaily.id}`);
      return;
    }
    const sprint = sprintForDate(sprints, todayIso());
    void create("daily", todayIso(), sprint ? sprint.id : null);
  }

  function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (newType !== "daily" && newSprintId === "") {
      setCreateError("Choisis le sprint concerné.");
      return;
    }
    void create(newType, newDate, newSprintId === "" ? null : newSprintId);
  }

  if (error) {
    return (
      <div className="page">
        <p className="error">{error}</p>
        <Link to={`/projects/${projectId}`}>Retour au projet</Link>
      </div>
    );
  }

  if (!project || !reports || !account) {
    return (
      <div className="page">
        <p>Chargement...</p>
      </div>
    );
  }

  const canManage = account.is_admin || project.created_by_account_id === account.id;
  const visible = filter === "all" ? reports : reports.filter((report) => report.type === filter);
  const orderedSprints = [...sprints].sort((a, b) => b.start_date.localeCompare(a.start_date));

  return (
    <AppShell title="Comptes-rendus" project={{ id: project.id, name: project.name }} canManage={canManage}>
      <div className="page page-wide">
        <PageHeader
          title="Comptes-rendus"
          subtitle="Daily, planification, review et rétrospective : remplis à plusieurs, exportés en Word."
          actions={
            <button type="button" className="button-link" onClick={handleTodayDaily} disabled={creating}>
              {todayDaily ? "Ouvrir le daily du jour" : "Démarrer le daily du jour"}
            </button>
          }
        />

        {!account.display_name && (
          <p className="notice">
            Ton nom n'est pas renseigné : les comptes-rendus afficheront ton adresse e-mail.{" "}
            <Link to="/profile">Renseigner mon nom</Link>
          </p>
        )}

        <form onSubmit={handleCreate} className="form report-create-form">
          <h2>Nouveau compte-rendu</h2>
          <div className="report-create-fields">
            <div className="field">
              <label htmlFor="report-type">Type</label>
              <select id="report-type" value={newType} onChange={(e) => setNewType(e.target.value as ReportType)}>
                {REPORT_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {REPORT_TYPE_LABELS[type]}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="report-date">Date</label>
              <input
                id="report-date"
                type="date"
                value={newDate}
                onChange={(e) => {
                  setNewDate(e.target.value);
                  const sprint = e.target.value ? sprintForDate(sprints, e.target.value) : undefined;
                  if (sprint) setNewSprintId(sprint.id);
                }}
                required
              />
            </div>
            <div className="field">
              <label htmlFor="report-sprint">Sprint</label>
              <select
                id="report-sprint"
                value={newSprintId}
                onChange={(e) => setNewSprintId(e.target.value ? Number(e.target.value) : "")}
              >
                <option value="">{newType === "daily" ? "Aucun" : "Choisir un sprint..."}</option>
                {orderedSprints.map((sprint) => (
                  <option key={sprint.id} value={sprint.id}>
                    {sprint.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
          {sprints.length === 0 && (
            <p className="meta">
              Aucun sprint pour l'instant : seuls les dailies sont possibles. Les sprints se créent dans les paramètres.
            </p>
          )}
          {createError && <p className="error">{createError}</p>}
          <div className="form-actions">
            <button type="submit" disabled={creating}>
              {creating ? "Création..." : "Créer"}
            </button>
          </div>
        </form>

        <section className="chart-section">
          <div className="report-list-header">
            <h2>Historique</h2>
            <div className="chip-row" role="group" aria-label="Filtrer par type">
              {(["all", ...REPORT_TYPES] as const).map((type) => (
                <button
                  key={type}
                  type="button"
                  className={filter === type ? "chip is-active" : "chip"}
                  aria-pressed={filter === type}
                  onClick={() => setFilter(type)}
                >
                  {type === "all" ? "Tous" : REPORT_TYPE_LABELS[type]}
                </button>
              ))}
            </div>
          </div>

          {visible.length === 0 ? (
            <p>Aucun compte-rendu pour l'instant.</p>
          ) : (
            <ul className="report-list">
              {visible.map((report) => (
                <li key={report.id}>
                  <Link to={`/projects/${project.id}/reports/${report.id}`} className="report-list-item">
                    <span className={`badge report-badge report-badge-${report.type}`}>
                      {REPORT_TYPE_LABELS[report.type]}
                    </span>
                    <span className="report-list-main">
                      <span className="report-list-date">{formatDate(report.meeting_date)}</span>
                      {report.sprint_name && <span className="meta">{report.sprint_name}</span>}
                    </span>
                    {report.updated_by_label && (
                      <span className="meta report-list-author">Modifié par {report.updated_by_label}</span>
                    )}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </AppShell>
  );
}
