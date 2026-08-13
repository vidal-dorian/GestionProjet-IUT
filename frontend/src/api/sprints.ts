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

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const message = body?.detail ?? "Une erreur est survenue.";
    throw new ApiError(response.status, message);
  }
  return response.json() as Promise<T>;
}

export function listSprints(projectId: number | string): Promise<Sprint[]> {
  return fetch(`${API_URL}/api/projects/${projectId}/sprints`).then((res) => handleResponse<Sprint[]>(res));
}

export function createSprint(projectId: number | string, input: SprintInput): Promise<SprintWriteResult> {
  return fetch(`${API_URL}/api/projects/${projectId}/sprints`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  }).then((res) => handleResponse<SprintWriteResult>(res));
}
