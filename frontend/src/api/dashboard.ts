import { devAuthHeaders } from "./authHeaders";
import { ApiError } from "./projects";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface HoursOverTimePoint {
  period: string;
  hours: number;
}

export interface HoursOverTime {
  granularity: "day" | "week";
  points: HoursOverTimePoint[];
}

export interface RecentTimeEntry {
  id: number;
  account_id: number;
  account_email: string;
  date: string;
  duration_hours: number;
  description: string;
}

export interface ProjectStats {
  total_hours: number;
  contributor_count: number;
  entry_count: number;
  average_hours_per_contributor: number;
}

export interface HoursByIssueItem {
  issue_number: number;
  issue_title: string;
  issue_url: string;
  hours: number;
}

export interface HoursByIssue {
  items: HoursByIssueItem[];
  unattached_hours: number;
}

export interface AccountHours {
  account_id: number;
  account_email: string;
  hours: number;
}

export interface SprintStats {
  sprint: { id: number; name: string; start_date: string; end_date: string };
  total_hours: number;
  hours_by_account: AccountHours[];
  hours_by_issue: HoursByIssue;
}

export interface HoursByCategoryItem {
  category_id: number;
  category_name: string;
  hours: number;
}

export interface HoursByCategory {
  items: HoursByCategoryItem[];
  unattached_hours: number;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const message = body?.detail ?? "Une erreur est survenue.";
    throw new ApiError(response.status, message);
  }
  return response.json() as Promise<T>;
}

export function getHoursOverTime(projectId: number | string): Promise<HoursOverTime> {
  return fetch(`${API_URL}/api/projects/${projectId}/dashboard/hours-over-time`, { credentials: "include", headers: devAuthHeaders() }).then((res) =>
    handleResponse<HoursOverTime>(res),
  );
}

export function getRecentEntries(projectId: number | string): Promise<RecentTimeEntry[]> {
  return fetch(`${API_URL}/api/projects/${projectId}/dashboard/recent-entries`, { credentials: "include", headers: devAuthHeaders() }).then((res) =>
    handleResponse<RecentTimeEntry[]>(res),
  );
}

export function getProjectStats(projectId: number | string): Promise<ProjectStats> {
  return fetch(`${API_URL}/api/projects/${projectId}/dashboard/stats`, { credentials: "include", headers: devAuthHeaders() }).then((res) =>
    handleResponse<ProjectStats>(res),
  );
}

export function getHoursByIssue(projectId: number | string): Promise<HoursByIssue> {
  return fetch(`${API_URL}/api/projects/${projectId}/dashboard/hours-by-issue`, { credentials: "include", headers: devAuthHeaders() }).then((res) =>
    handleResponse<HoursByIssue>(res),
  );
}

export function getSprintStats(projectId: number | string, sprintId: number | string): Promise<SprintStats> {
  return fetch(`${API_URL}/api/projects/${projectId}/dashboard/sprints/${sprintId}/stats`, { credentials: "include", headers: devAuthHeaders() }).then((res) =>
    handleResponse<SprintStats>(res),
  );
}

export function getHoursByCategory(projectId: number | string): Promise<HoursByCategory> {
  return fetch(`${API_URL}/api/projects/${projectId}/dashboard/hours-by-category`, { credentials: "include", headers: devAuthHeaders() }).then((res) =>
    handleResponse<HoursByCategory>(res),
  );
}
