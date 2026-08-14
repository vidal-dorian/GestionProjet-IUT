import { devAuthHeaders } from "./authHeaders";
import { ApiError } from "./projects";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface Sprint {
  id: number;
  project_id: number;
  name: string;
  start_date: string;
  end_date: string;
  created_at: string;
}

export interface SprintInput {
  name: string;
  start_date: string;
  end_date: string;
}

export interface SprintWriteResult {
  sprint: Sprint;
  overlap_warning: string | null;
}

export interface SprintRoleAssignment {
  role_id: number;
  role_name: string;
  account_id: number;
  account_email: string;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const message = body?.detail ?? "Une erreur est survenue.";
    throw new ApiError(response.status, message);
  }
  return response.json() as Promise<T>;
}

export function listSprints(projectId: number | string): Promise<Sprint[]> {
  return fetch(`${API_URL}/api/projects/${projectId}/sprints`, {
    credentials: "include",
    headers: devAuthHeaders(),
  }).then((res) => handleResponse<Sprint[]>(res));
}

export function createSprint(projectId: number | string, input: SprintInput): Promise<SprintWriteResult> {
  return fetch(`${API_URL}/api/projects/${projectId}/sprints`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", ...devAuthHeaders() },
    body: JSON.stringify(input),
  }).then((res) => handleResponse<SprintWriteResult>(res));
}

export function listSprintRoleAssignments(
  projectId: number | string,
  sprintId: number | string,
): Promise<SprintRoleAssignment[]> {
  return fetch(`${API_URL}/api/projects/${projectId}/sprints/${sprintId}/role-assignments`, {
    credentials: "include",
    headers: devAuthHeaders(),
  }).then((res) => handleResponse<SprintRoleAssignment[]>(res));
}

export function replaceSprintRoleAssignments(
  projectId: number | string,
  sprintId: number | string,
  assignments: { role_id: number; account_id: number }[],
): Promise<SprintRoleAssignment[]> {
  return fetch(`${API_URL}/api/projects/${projectId}/sprints/${sprintId}/role-assignments`, {
    method: "PUT",
    credentials: "include",
    headers: { "Content-Type": "application/json", ...devAuthHeaders() },
    body: JSON.stringify({ assignments }),
  }).then((res) => handleResponse<SprintRoleAssignment[]>(res));
}
