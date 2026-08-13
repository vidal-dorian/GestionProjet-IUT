const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface Project {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
}

export interface ProjectSummary {
  id: number;
  name: string;
  description: string | null;
  member_count: number;
}

export interface ProjectInput {
  name: string;
  description?: string;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const message = body?.detail ?? "Une erreur est survenue.";
    throw new ApiError(response.status, message);
  }
  return response.json() as Promise<T>;
}

export function listProjects(): Promise<ProjectSummary[]> {
  return fetch(`${API_URL}/api/projects`).then((res) => handleResponse<ProjectSummary[]>(res));
}

export function createProject(input: ProjectInput): Promise<Project> {
  return fetch(`${API_URL}/api/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  }).then((res) => handleResponse<Project>(res));
}

export function getProject(id: number | string): Promise<Project> {
  return fetch(`${API_URL}/api/projects/${id}`).then((res) => handleResponse<Project>(res));
}
