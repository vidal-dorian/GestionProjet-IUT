import { ApiError } from "./projects";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface TimeEntry {
  id: number;
  project_id: number;
  member_id: number;
  date: string;
  duration_hours: number;
  description: string;
  created_at: string;
}

export interface TimeEntryInput {
  date: string;
  duration_hours: number;
  description: string;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const message = body?.detail ?? "Une erreur est survenue.";
    throw new ApiError(response.status, message);
  }
  return response.json() as Promise<T>;
}

export function listMyTimeEntries(projectId: number | string): Promise<TimeEntry[]> {
  return fetch(`${API_URL}/api/projects/${projectId}/time-entries`, { credentials: "include" }).then((res) =>
    handleResponse<TimeEntry[]>(res),
  );
}

export function createTimeEntry(projectId: number | string, input: TimeEntryInput): Promise<TimeEntry> {
  return fetch(`${API_URL}/api/projects/${projectId}/time-entries`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(input),
  }).then((res) => handleResponse<TimeEntry>(res));
}
