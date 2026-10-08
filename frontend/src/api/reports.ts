import { devAuthHeaders } from "./authHeaders";
import { ApiError, extractErrorMessage } from "./projects";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export type ReportType = "daily" | "sprint_planning" | "sprint_review" | "retrospective";

export const REPORT_TYPE_LABELS: Record<ReportType, string> = {
  daily: "Daily",
  sprint_planning: "Planification de sprint",
  sprint_review: "Review de sprint",
  retrospective: "Rétrospective",
};

export type Balance = "all" | "time_quality" | "time_scope" | "quality_scope" | "time" | "quality" | "scope";

export interface UserStoryRow {
  reference: string;
  name: string;
}

/* Tous les champs possibles, quel que soit le type : le backend ignore ceux
   qui ne concernent pas le type du compte-rendu et complète les manquants. */
export interface ReportContent {
  participant_ids: number[];
  // Daily
  scrum_master_notes?: string;
  balance?: Balance;
  balance_x?: number | null;
  balance_y?: number | null;
  // Planification / review
  client?: string;
  topics?: string;
  hours_per_member?: number | null;
  objectives?: string;
  user_stories?: UserStoryRow[];
  // Rétrospective
  scrum_master?: string;
  product_owner?: string;
  went_well?: string;
  to_improve?: string;
  actions?: string;
  product_owner_notes?: string;
  include_burndown?: boolean;
  burndown_comment?: string;
}

export interface ReportSummary {
  id: number;
  project_id: number;
  type: ReportType;
  sprint_id: number | null;
  sprint_name: string | null;
  meeting_date: string;
  created_by_label: string | null;
  updated_at: string;
  updated_by_label: string | null;
}

export interface TeamMember {
  account_id: number;
  label: string;
  email: string;
  roles: string[];
}

export interface DailyEntry {
  account_id: number;
  done: string;
  todo: string;
  blockers: string;
  updated_at: string;
  updated_by_label: string | null;
}

export interface Report extends ReportSummary {
  content: ReportContent;
  version: number;
  team: TeamMember[];
  daily_entries: DailyEntry[];
  can_delete: boolean;
}

export interface ReportUpdate {
  sprint_id: number | null;
  meeting_date: string;
  content: ReportContent;
  version: number;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const message = extractErrorMessage(body?.detail, response.status);
    throw new ApiError(response.status, message);
  }
  return response.json() as Promise<T>;
}

function reportsUrl(projectId: number | string): string {
  return `${API_URL}/api/projects/${projectId}/reports`;
}

export function listReports(projectId: number | string): Promise<ReportSummary[]> {
  return fetch(reportsUrl(projectId), { credentials: "include", headers: devAuthHeaders() }).then((res) =>
    handleResponse<ReportSummary[]>(res),
  );
}

export function createReport(
  projectId: number | string,
  input: { type: ReportType; sprint_id: number | null; meeting_date: string },
): Promise<Report> {
  return fetch(reportsUrl(projectId), {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", ...devAuthHeaders() },
    body: JSON.stringify(input),
  }).then((res) => handleResponse<Report>(res));
}

export function getReport(projectId: number | string, reportId: number | string): Promise<Report> {
  return fetch(`${reportsUrl(projectId)}/${reportId}`, { credentials: "include", headers: devAuthHeaders() }).then(
    (res) => handleResponse<Report>(res),
  );
}

export function updateReport(projectId: number | string, reportId: number | string, input: ReportUpdate): Promise<Report> {
  return fetch(`${reportsUrl(projectId)}/${reportId}`, {
    method: "PUT",
    credentials: "include",
    headers: { "Content-Type": "application/json", ...devAuthHeaders() },
    body: JSON.stringify(input),
  }).then((res) => handleResponse<Report>(res));
}

export function deleteReport(projectId: number | string, reportId: number | string): Promise<void> {
  return fetch(`${reportsUrl(projectId)}/${reportId}`, {
    method: "DELETE",
    credentials: "include",
    headers: devAuthHeaders(),
  }).then(async (res) => {
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new ApiError(res.status, extractErrorMessage(body?.detail, res.status));
    }
  });
}

export function saveDailyEntry(
  projectId: number | string,
  reportId: number | string,
  accountId: number,
  input: { done: string; todo: string; blockers: string },
): Promise<Report> {
  return fetch(`${reportsUrl(projectId)}/${reportId}/daily-entries/${accountId}`, {
    method: "PUT",
    credentials: "include",
    headers: { "Content-Type": "application/json", ...devAuthHeaders() },
    body: JSON.stringify(input),
  }).then((res) => handleResponse<Report>(res));
}

export function getSuggestedUserStories(
  projectId: number | string,
  reportId: number | string,
  sprintId: number | null,
): Promise<{ user_stories: UserStoryRow[]; source_label: string | null }> {
  const query = sprintId !== null ? `?sprint_id=${sprintId}` : "";
  return fetch(`${reportsUrl(projectId)}/${reportId}/suggested-user-stories${query}`, {
    credentials: "include",
    headers: devAuthHeaders(),
  }).then((res) => handleResponse<{ user_stories: UserStoryRow[]; source_label: string | null }>(res));
}

export async function downloadReportExport(projectId: number | string, reportId: number | string): Promise<void> {
  const response = await fetch(`${reportsUrl(projectId)}/${reportId}/export`, {
    credentials: "include",
    headers: devAuthHeaders(),
  });
  if (!response.ok) {
    throw new ApiError(response.status, "Impossible d'exporter ce compte-rendu pour le moment.");
  }
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = /filename="?([^"]+)"?/.exec(disposition);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = match ? match[1] : "compte-rendu.docx";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
