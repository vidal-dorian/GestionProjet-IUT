const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface Project {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
  github_repo: string | null;
  github_last_synced_at: string | null;
}

export interface GithubIssue {
  id: number;
  number: number;
  title: string;
  state: string;
  labels: string[];
  url: string;
}

export interface GithubSyncResult {
  synced_at: string;
  issue_count: number;
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
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
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

export function updateProject(id: number | string, input: ProjectInput): Promise<Project> {
  return fetch(`${API_URL}/api/projects/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  }).then((res) => handleResponse<Project>(res));
}

export function deleteProject(id: number | string): Promise<void> {
  return fetch(`${API_URL}/api/projects/${id}`, { method: "DELETE" }).then((res) => {
    if (!res.ok) throw new ApiError(res.status, "Impossible de supprimer ce projet.");
  });
}

export function linkGithubRepo(id: number | string, repo: string): Promise<Project> {
  return fetch(`${API_URL}/api/projects/${id}/github`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo }),
  }).then((res) => handleResponse<Project>(res));
}

export function syncGithubIssues(id: number | string): Promise<GithubSyncResult> {
  return fetch(`${API_URL}/api/projects/${id}/github/sync`, { method: "POST" }).then((res) =>
    handleResponse<GithubSyncResult>(res),
  );
}

export function listGithubIssues(id: number | string): Promise<GithubIssue[]> {
  return fetch(`${API_URL}/api/projects/${id}/github/issues`).then((res) => handleResponse<GithubIssue[]>(res));
}
