import { type FormEvent, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ApiError, getProject, type Project } from "../api/projects";
import {
  deleteReport,
  downloadReportExport,
  getReport,
  getSuggestedUserStories,
  type Report,
  type ReportContent,
  REPORT_TYPE_LABELS,
  saveDailyEntry,
  updateReport,
  type UserStoryRow,
} from "../api/reports";
import { listSprints, type Sprint } from "../api/sprints";
import AppShell from "../components/AppShell";
import BalanceDiagram from "../components/BalanceDiagram";
import DailyEntryCard, { type Answers } from "../components/DailyEntryCard";
import PageHeader from "../components/PageHeader";
import UserStoryTableEditor from "../components/UserStoryTableEditor";
import { useAuth } from "../context/AuthContext";

interface Draft {
  sprint_id: number | null;
  meeting_date: string;
  content: ReportContent;
}

// Fréquence de synchronisation avec les modifications des autres membres.
const SYNC_INTERVAL_MS = 4000;

const BULLET_HINT = "Une ligne par point ; commence une ligne par des espaces pour en faire un sous-point.";

function toDraft(report: Report): Draft {
  return { sprint_id: report.sprint_id, meeting_date: report.meeting_date, content: report.content };
}

function formatDate(isoDate: string): string {
  return new Date(`${isoDate}T00:00:00`).toLocaleDateString("fr-FR");
}

export default function ReportEditorPage() {
  const { projectId, reportId } = useParams<{ projectId: string; reportId: string }>();
  const navigate = useNavigate();
  const { account } = useAuth();
  const [project, setProject] = useState<Project | null>(null);
  const [sprints, setSprints] = useState<Sprint[]>([]);
  const [report, setReport] = useState<Report | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [dirty, setDirty] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [conflict, setConflict] = useState(false);
  const [savedAt, setSavedAt] = useState<Date | null>(null);
  const [exporting, setExporting] = useState(false);
  const [filling, setFilling] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [remoteChanged, setRemoteChanged] = useState(false);
  const reportRef = useRef<Report | null>(null);
  const dirtyRef = useRef(false);
  // Incrémenté à chaque début et fin d'enregistrement d'une carte du daily :
  // une synchronisation lancée avant ne doit pas réafficher l'ancienne version.
  const entrySavesRef = useRef(0);
  reportRef.current = report;
  dirtyRef.current = dirty;

  function applyServerReport(next: Report) {
    setReport(next);
    setDraft(toDraft(next));
    setDirty(false);
    setConflict(false);
    setRemoteChanged(false);
  }

  useEffect(() => {
    if (!projectId || !reportId) return;
    Promise.all([getProject(projectId), listSprints(projectId), getReport(projectId, reportId)])
      .then(([projectData, sprintData, reportData]) => {
        setProject(projectData);
        setSprints(sprintData);
        applyServerReport(reportData);
      })
      .catch(() => setLoadError("Ce compte-rendu est introuvable."));
  }, [projectId, reportId]);

  /* Synchronisation en direct (sondage régulier plutôt que WebSocket : simple,
     et suffisant pour une équipe de quelques personnes) : les réponses des
     autres au daily apparaissent sans recharger, et le reste du formulaire
     suit les enregistrements des autres tant qu'on ne le modifie pas soi-même. */
  useEffect(() => {
    if (!projectId || !reportId) return;
    let cancelled = false;
    const timer = window.setInterval(async () => {
      if (document.visibilityState !== "visible" || !reportRef.current) return;
      const savesAtStart = entrySavesRef.current;
      let fresh: Report;
      try {
        fresh = await getReport(projectId, reportId);
      } catch {
        return;
      }
      const current = reportRef.current;
      if (cancelled || !current || fresh.version < current.version) return;
      const entries = entrySavesRef.current === savesAtStart ? fresh.daily_entries : current.daily_entries;
      if (dirtyRef.current) {
        // Formulaire en cours de modification : on ne touche qu'aux réponses du
        // daily, et on prévient si quelqu'un a enregistré le reste entre-temps.
        if (fresh.version !== current.version) setRemoteChanged(true);
        setReport({ ...current, team: fresh.team, daily_entries: entries });
      } else {
        setReport({ ...fresh, daily_entries: entries });
        if (fresh.version !== current.version) setDraft(toDraft(fresh));
      }
    }, SYNC_INTERVAL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [projectId, reportId]);

  // Prévient avant de quitter la page avec des modifications non enregistrées.
  useEffect(() => {
    if (!dirty) return;
    function onBeforeUnload(event: BeforeUnloadEvent) {
      event.preventDefault();
    }
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [dirty]);

  function patchDraft(patch: Partial<Draft>) {
    setDraft((current) => (current ? { ...current, ...patch } : current));
    setDirty(true);
    setSavedAt(null);
  }

  function patchContent(patch: Partial<ReportContent>) {
    setDraft((current) => (current ? { ...current, content: { ...current.content, ...patch } } : current));
    setDirty(true);
    setSavedAt(null);
  }

  async function save(): Promise<boolean> {
    if (!projectId || !report || !draft) return false;
    setSaving(true);
    setSaveError(null);
    try {
      const saved = await updateReport(projectId, report.id, { ...draft, version: report.version });
      applyServerReport(saved);
      setSavedAt(new Date());
      return true;
    } catch (err) {
      if (err instanceof ApiError && err.status === 409 && err.message.includes("modifié")) setConflict(true);
      setSaveError(err instanceof ApiError ? err.message : "Impossible d'enregistrer pour le moment.");
      return false;
    } finally {
      setSaving(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void save();
  }

  async function handleReload() {
    if (!projectId || !reportId) return;
    const fresh = await getReport(projectId, reportId);
    applyServerReport(fresh);
    setSaveError(null);
  }

  async function handleExport() {
    if (!projectId || !report) return;
    if (dirty && !(await save())) return;
    setExporting(true);
    try {
      await downloadReportExport(projectId, report.id);
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : "Impossible d'exporter pour le moment.");
    } finally {
      setExporting(false);
    }
  }

  async function handleDelete() {
    if (!projectId || !report) return;
    if (!window.confirm("Supprimer définitivement ce compte-rendu ?")) return;
    setDeleting(true);
    try {
      await deleteReport(projectId, report.id);
      setDirty(false);
      navigate(`/projects/${projectId}/reports`);
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : "Impossible de supprimer pour le moment.");
      setDeleting(false);
    }
  }

  async function handleFillUserStories() {
    if (!projectId || !report || !draft) return;
    setFilling(true);
    setSaveError(null);
    try {
      const suggestion = await getSuggestedUserStories(projectId, report.id, draft.sprint_id);
      const current = draft.content.user_stories ?? [];
      const filled = current.some((row) => row.reference.trim() !== "#" && (row.reference.trim() || row.name.trim()));
      if (filled && !window.confirm("Remplacer le tableau actuel par les US trouvées sur GitHub ?")) return;
      patchContent({ user_stories: suggestion.user_stories });
      if (suggestion.user_stories.length === 0) {
        setSaveError(
          report.type === "sprint_review"
            ? `Aucune US fermée labellisée « ${suggestion.source_label ?? ""} » sur GitHub (pense à synchroniser les issues).`
            : `Aucune US labellisée « ${suggestion.source_label ?? ""} » sur GitHub (pense à synchroniser les issues).`,
        );
      }
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : "Impossible de récupérer les US pour le moment.");
    } finally {
      setFilling(false);
    }
  }

  async function handleSaveEntry(accountId: number, answers: Answers) {
    if (!projectId || !reportId) return;
    entrySavesRef.current += 1;
    try {
      const saved = await saveDailyEntry(projectId, reportId, accountId, answers);
      // On ne reprend que les réponses : le reste du formulaire peut contenir
      // des modifications locales pas encore enregistrées.
      setReport((current) => (current ? { ...current, daily_entries: saved.daily_entries } : current));
    } finally {
      entrySavesRef.current += 1;
    }
  }

  if (loadError) {
    return (
      <div className="page">
        <p className="error">{loadError}</p>
        <Link to={`/projects/${projectId}/reports`}>Retour aux comptes-rendus</Link>
      </div>
    );
  }

  if (!project || !report || !draft || !account) {
    return (
      <div className="page">
        <p>Chargement...</p>
      </div>
    );
  }

  const canManage = account.is_admin || project.created_by_account_id === account.id;
  const content = draft.content;
  const participantIds = new Set(content.participant_ids);
  const participants = report.team.filter((member) => participantIds.has(member.account_id));
  // Ma carte d'abord : c'est celle que chacun vient remplir.
  const orderedParticipants = [
    ...participants.filter((member) => member.account_id === account.id),
    ...participants.filter((member) => member.account_id !== account.id),
  ];
  const sprintName = sprints.find((sprint) => sprint.id === draft.sprint_id)?.name;
  const title =
    report.type === "daily"
      ? `Daily du ${formatDate(draft.meeting_date)}`
      : `${REPORT_TYPE_LABELS[report.type]}${sprintName ? ` — ${sprintName}` : ""}`;
  const orderedSprints = [...sprints].sort((a, b) => b.start_date.localeCompare(a.start_date));

  function toggleParticipant(accountId: number, checked: boolean) {
    const next = checked
      ? [...content.participant_ids, accountId]
      : content.participant_ids.filter((id) => id !== accountId);
    patchContent({ participant_ids: next });
  }

  function textField(key: keyof ReportContent, label: string, options: { rows?: number; hint?: string; placeholder?: string } = {}) {
    const id = `report-${String(key)}`;
    return (
      <div className="field">
        <label htmlFor={id}>{label}</label>
        <textarea
          id={id}
          rows={options.rows ?? 4}
          maxLength={10000}
          value={(content[key] as string | undefined) ?? ""}
          placeholder={options.placeholder}
          onChange={(e) => patchContent({ [key]: e.target.value })}
        />
        {options.hint && <p className="meta">{options.hint}</p>}
      </div>
    );
  }

  function inputField(key: keyof ReportContent, label: string, placeholder?: string) {
    const id = `report-${String(key)}`;
    return (
      <div className="field">
        <label htmlFor={id}>{label}</label>
        <input
          id={id}
          type="text"
          maxLength={200}
          value={(content[key] as string | undefined) ?? ""}
          placeholder={placeholder}
          onChange={(e) => patchContent({ [key]: e.target.value })}
        />
      </div>
    );
  }

  const hours = content.hours_per_member ?? null;

  return (
    <AppShell title="Compte-rendu" project={{ id: project.id, name: project.name }} canManage={canManage}>
      <div className="page page-wide">
        <Link to={`/projects/${project.id}/reports`} className="back-link">
          ← Comptes-rendus
        </Link>
        <PageHeader
          title={title}
          subtitle={
            report.updated_by_label
              ? `Dernière modification par ${report.updated_by_label}`
              : REPORT_TYPE_LABELS[report.type]
          }
          actions={
            <>
              <button type="button" className="button-link" onClick={handleExport} disabled={exporting || saving}>
                {exporting ? "Export..." : "Exporter en Word"}
              </button>
              {report.can_delete && (
                <button type="button" className="button-secondary" onClick={handleDelete} disabled={deleting}>
                  Supprimer
                </button>
              )}
            </>
          }
        />

        <form onSubmit={handleSubmit} className="report-editor">
          <section className="chart-section form-section">
            <h2>Informations générales</h2>
            <div className="report-create-fields">
              <div className="field">
                <label htmlFor="report-date">Date</label>
                <input
                  id="report-date"
                  type="date"
                  value={draft.meeting_date}
                  onChange={(e) => e.target.value && patchDraft({ meeting_date: e.target.value })}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="report-sprint">Sprint</label>
                <select
                  id="report-sprint"
                  value={draft.sprint_id ?? ""}
                  onChange={(e) => patchDraft({ sprint_id: e.target.value ? Number(e.target.value) : null })}
                >
                  {report.type === "daily" && <option value="">Aucun</option>}
                  {orderedSprints.map((sprint) => (
                    <option key={sprint.id} value={sprint.id}>
                      {sprint.name}
                    </option>
                  ))}
                </select>
              </div>
              {(report.type === "sprint_planning" || report.type === "sprint_review") &&
                inputField("client", "Client", "Nom du client")}
            </div>

            <fieldset className="participants">
              <legend>{report.type === "daily" ? "Personnes présentes" : "Participants (équipe)"}</legend>
              {report.team.map((member) => (
                <label key={member.account_id} className="checkbox-row">
                  <input
                    type="checkbox"
                    checked={participantIds.has(member.account_id)}
                    onChange={(e) => toggleParticipant(member.account_id, e.target.checked)}
                  />
                  <span>
                    {member.label}
                    {member.roles.length > 0 && <span className="meta"> · {member.roles.join(", ")}</span>}
                  </span>
                </label>
              ))}
              <p className="meta">
                Les noms viennent du profil de chacun (<Link to="/profile">Mon profil</Link>) et les rôles de
                l'attribution sur le sprint (page Sprints).
              </p>
            </fieldset>

            {report.type === "retrospective" && (
              <div className="report-create-fields">
                {inputField("scrum_master", "Scrum Master")}
                {inputField("product_owner", "Product Owner")}
              </div>
            )}
          </section>

          {report.type === "daily" && (
            <>
              <p className="live-hint">
                <span className="live-dot" aria-hidden="true" />
                Chacun remplit sa carte en même temps : tout s'enregistre automatiquement et les réponses des autres
                apparaissent en direct.
              </p>
              <section className="daily-grid" aria-label="Réponses de l'équipe">
                {orderedParticipants.length === 0 && (
                  <p className="meta">Coche les personnes présentes pour faire apparaître leur partie.</p>
                )}
                {orderedParticipants.map((member) => (
                  <DailyEntryCard
                    key={member.account_id}
                    member={member}
                    isMe={member.account_id === account.id}
                    entry={report.daily_entries.find((entry) => entry.account_id === member.account_id)}
                    onSave={(answers) => handleSaveEntry(member.account_id, answers)}
                  />
                ))}
              </section>
              <section className="chart-section form-section">
                <h2>Scrum Master</h2>
                {textField("scrum_master_notes", "Notes du Scrum Master", { rows: 3, hint: BULLET_HINT })}
                <div className="field">
                  <span className="field-label">Équilibre du projet (temps / qualité / cahier des charges)</span>
                  <BalanceDiagram
                    x={content.balance_x}
                    y={content.balance_y}
                    balance={content.balance}
                    onChange={(point) => patchContent({ balance_x: point.x, balance_y: point.y })}
                  />
                  <p className="meta">
                    Clique ou fais glisser le point rouge pour indiquer où se situe le projet. Il apparaît au même
                    endroit dans le daily exporté.
                  </p>
                </div>
              </section>
            </>
          )}

          {report.type === "sprint_planning" && (
            <section className="chart-section form-section">
              <h2>Contenu de la planification</h2>
              {textField("topics", "Sujet de la réunion", { rows: 5, hint: BULLET_HINT })}
              <div className="field">
                <label htmlFor="report-hours">Heures planifiées par membre</label>
                <input
                  id="report-hours"
                  type="number"
                  min={0}
                  step={0.5}
                  value={hours ?? ""}
                  onChange={(e) => patchContent({ hours_per_member: e.target.value === "" ? null : Number(e.target.value) })}
                />
                {hours !== null && (
                  <p className="meta">
                    Capacité totale : {Math.round(hours * participants.length * 100) / 100} heures ({participants.length}{" "}
                    participant{participants.length > 1 ? "s" : ""})
                  </p>
                )}
              </div>
              <h3 className="form-subheading">Items de backlog proposés pour l'itération</h3>
              <UserStoryTableEditor
                rows={content.user_stories ?? []}
                onChange={(rows: UserStoryRow[]) => patchContent({ user_stories: rows })}
                onFillFromGithub={handleFillUserStories}
                filling={filling}
                fillLabel="Remplir avec les US du sprint"
              />
            </section>
          )}

          {report.type === "sprint_review" && (
            <section className="chart-section form-section">
              <h2>Contenu de la review</h2>
              {textField("objectives", "Objectifs du sprint", {
                rows: 5,
                hint: `${BULLET_HINT} Repris de la planification du même sprint s'il y en a une.`,
              })}
              <h3 className="form-subheading">User stories réalisées</h3>
              <UserStoryTableEditor
                rows={content.user_stories ?? []}
                onChange={(rows: UserStoryRow[]) => patchContent({ user_stories: rows })}
                onFillFromGithub={handleFillUserStories}
                filling={filling}
                fillLabel="Remplir avec les US clôturées du sprint"
              />
              <p className="meta">
                Les US clôturées sont celles fermées sur GitHub et labellisées du nom du sprint (même règle que le
                burndown).
              </p>
            </section>
          )}

          {report.type === "retrospective" && (
            <section className="chart-section form-section">
              <h2>Contenu de la rétrospective</h2>
              {textField("went_well", "Ce qui a bien fonctionné", { hint: BULLET_HINT })}
              {textField("to_improve", "Ce qui est à améliorer", { hint: BULLET_HINT })}
              {textField("actions", "Actions d'amélioration", { hint: BULLET_HINT })}
              {textField("product_owner_notes", "Notes du Product Owner", { rows: 5 })}
              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={content.include_burndown ?? true}
                  onChange={(e) => patchContent({ include_burndown: e.target.checked })}
                />
                <span>Inclure le burndown chart du sprint (calculé depuis GitHub)</span>
              </label>
              {(content.include_burndown ?? true) &&
                textField("burndown_comment", "Commentaire du burndown", {
                  rows: 3,
                  placeholder: "Dans cette itération...",
                })}
            </section>
          )}

          <div className="report-save-bar">
            <span className="meta">
              {[
                dirty
                  ? "Modifications non enregistrées"
                  : savedAt
                    ? `Enregistré à ${savedAt.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}`
                    : "",
                report.type === "daily"
                  ? "Ce bouton enregistre les informations générales et la partie Scrum Master ; les cartes s'enregistrent seules."
                  : "",
              ]
                .filter(Boolean)
                .join(" — ")}
            </span>
            {saveError && <p className="error">{saveError}</p>}
            {remoteChanged && !conflict && (
              <p className="warning">
                Quelqu'un vient d'enregistrer ce compte-rendu pendant que tu le modifiais : recharge pour voir ses
                changements (les tiens seront perdus), ou enregistre pour être averti du conflit.
              </p>
            )}
            {(conflict || remoteChanged) && (
              <button type="button" className="button-secondary" onClick={handleReload}>
                Recharger (perd mes modifications)
              </button>
            )}
            <button type="submit" className="button-link" disabled={saving || !dirty}>
              {saving ? "Enregistrement..." : "Enregistrer"}
            </button>
          </div>
        </form>
      </div>
    </AppShell>
  );
}
