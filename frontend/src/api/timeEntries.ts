import type { Account } from "./auth";
import { devAuthHeaders } from "./authHeaders";
import type { Category } from "./categories";
import { ApiError, type GithubIssue } from "./projects";
import type { Sprint } from "./sprints";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface TimeEntry {
  id: number;
  project_id: number;
  account_id: number;
  account: Account;
  date: string;
  duration_hours: number;
  description: string;
  created_at: string;
  github_issue_id: number | null;
  github_issue: GithubIssue | null;
  sprint_id: number | null;
  sprint: Sprint | null;
  category_id: number | null;
  category: Category | null;
}

export interface TimeEntryInput {
  date: string;
  duration_hours: number;
  description: string;
  github_issue_id?: number | null;
  sprint_id?: number | null;
  category_id?: number | null;
}

function extractErrorMessage(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    // FastAPI renvoie une liste d'erreurs de validation Pydantic ({ msg, loc, ... })
    // plutôt qu'un message simple pour les erreurs 422.
    const messages = detail
      .map((item) => (typeof item?.msg === "string" ? item.msg.replace(/^Value error,\s*/, "") : null))
      .filter((msg): msg is string => Boolean(msg));
    if (messages.length > 0) return messages.join(" ");
  }
  return "Une erreur est survenue.";
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, extractErrorMessage(body?.detail));
  }
  return response.json() as Promise<T>;
}

export function listMyTimeEntries(projectId: number | string): Promise<TimeEntry[]> {
  return fetch(`${API_URL}/api/projects/${projectId}/time-entries`, {
    credentials: "include",
    headers: devAuthHeaders(),
  }).then((res) => handleResponse<TimeEntry[]>(res));
}

export function createTimeEntry(projectId: number | string, input: TimeEntryInput): Promise<TimeEntry> {
  return fetch(`${API_URL}/api/projects/${projectId}/time-entries`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...devAuthHeaders() },
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
    headers: { "Content-Type": "application/json", ...devAuthHeaders() },
    credentials: "include",
    body: JSON.stringify(input),
  }).then((res) => handleResponse<TimeEntry>(res));
}

export function deleteTimeEntry(projectId: number | string, entryId: number): Promise<void> {
  return fetch(`${API_URL}/api/projects/${projectId}/time-entries/${entryId}`, {
    method: "DELETE",
    credentials: "include",
    headers: devAuthHeaders(),
  }).then((res) => {
    if (!res.ok) throw new ApiError(res.status, "Impossible de supprimer cette entrée.");
  });
}
