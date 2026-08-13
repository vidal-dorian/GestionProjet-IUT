import { ApiError, type GithubIssue } from "./projects";
import type { Sprint } from "./sprints";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface TimeEntry {
  id: number;
  project_id: number;
  member_id: number;
  date: string;
  duration_hours: number;
  description: string;
  created_at: string;
  github_issue_id: number | null;
  github_issue: GithubIssue | null;
  sprint_id: number | null;
  sprint: Sprint | null;
}

export interface TimeEntryInput {
  date: string;
  duration_hours: number;
  description: string;
  github_issue_id?: number | null;
  sprint_id?: number | null;
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

export function updateTimeEntry(
  projectId: number | string,
  entryId: number,
  input: TimeEntryInput,
): Promise<TimeEntry> {
  return fetch(`${API_URL}/api/projects/${projectId}/time-entries/${entryId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(input),
  }).then((res) => handleResponse<TimeEntry>(res));
}

export function deleteTimeEntry(projectId: number | string, entryId: number): Promise<void> {
  return fetch(`${API_URL}/api/projects/${projectId}/time-entries/${entryId}`, {
    method: "DELETE",
    credentials: "include",
  }).then((res) => {
    if (!res.ok) throw new ApiError(res.status, "Impossible de supprimer cette entrée.");
  });
}
