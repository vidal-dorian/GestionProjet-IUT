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
  member_id: number;
  member_name: string;
  date: string;
  duration_hours: number;
  description: string;
}

export interface ProjectStats {
  total_hours: number;
  member_count: number;
  active_member_count: number;
  entry_count: number;
  average_hours_per_member: number;
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
  return fetch(`${API_URL}/api/projects/${projectId}/dashboard/hours-over-time`).then((res) =>
    handleResponse<HoursOverTime>(res),
  );
}

export function getRecentEntries(projectId: number | string): Promise<RecentTimeEntry[]> {
  return fetch(`${API_URL}/api/projects/${projectId}/dashboard/recent-entries`).then((res) =>
    handleResponse<RecentTimeEntry[]>(res),
  );
}

export function getProjectStats(projectId: number | string): Promise<ProjectStats> {
  return fetch(`${API_URL}/api/projects/${projectId}/dashboard/stats`).then((res) =>
    handleResponse<ProjectStats>(res),
  );
}
