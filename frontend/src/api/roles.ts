import { devAuthHeaders } from "./authHeaders";
import { ApiError } from "./projects";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface TeamRole {
  id: number;
  project_id: number;
  name: string;
  created_at: string;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const message = body?.detail ?? "Une erreur est survenue.";
    throw new ApiError(response.status, message);
  }
  return response.json() as Promise<T>;
}

export function listRoles(projectId: number | string): Promise<TeamRole[]> {
  return fetch(`${API_URL}/api/projects/${projectId}/roles`, {
    credentials: "include",
    headers: devAuthHeaders(),
  }).then((res) => handleResponse<TeamRole[]>(res));
}

export function createRole(projectId: number | string, name: string): Promise<TeamRole> {
  return fetch(`${API_URL}/api/projects/${projectId}/roles`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", ...devAuthHeaders() },
    body: JSON.stringify({ name }),
  }).then((res) => handleResponse<TeamRole>(res));
}

export function renameRole(projectId: number | string, roleId: number, name: string): Promise<TeamRole> {
  return fetch(`${API_URL}/api/projects/${projectId}/roles/${roleId}`, {
    method: "PUT",
    credentials: "include",
    headers: { "Content-Type": "application/json", ...devAuthHeaders() },
    body: JSON.stringify({ name }),
  }).then((res) => handleResponse<TeamRole>(res));
}

export function deleteRole(projectId: number | string, roleId: number): Promise<void> {
  return fetch(`${API_URL}/api/projects/${projectId}/roles/${roleId}`, {
    method: "DELETE",
    credentials: "include",
    headers: devAuthHeaders(),
  }).then((res) => {
    if (!res.ok) throw new ApiError(res.status, "Impossible de supprimer ce rôle.");
  });
}
