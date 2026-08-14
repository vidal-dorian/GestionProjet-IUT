import { devAuthHeaders } from "./authHeaders";
import { ApiError } from "./projects";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface Category {
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

export function listCategories(projectId: number | string): Promise<Category[]> {
  return fetch(`${API_URL}/api/projects/${projectId}/categories`, {
    credentials: "include",
    headers: devAuthHeaders(),
  }).then((res) => handleResponse<Category[]>(res));
}

export function createCategory(projectId: number | string, name: string): Promise<Category> {
  return fetch(`${API_URL}/api/projects/${projectId}/categories`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", ...devAuthHeaders() },
    body: JSON.stringify({ name }),
  }).then((res) => handleResponse<Category>(res));
}
