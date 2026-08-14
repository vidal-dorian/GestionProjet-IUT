import { devAuthHeaders } from "./authHeaders";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface Project {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
  github_repo: string | null;
  github_last_synced_at: string | null;
  github_label_filter: string[];
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
  contributor_count: number;
  is_member: boolean;
}

export interface Contributor {
  account_id: number;
  account_email: string;
  hours: number;
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
  return fetch(`${API_URL}/api/projects`, { credentials: "include", headers: devAuthHeaders() }).then((res) =>
    handleResponse<ProjectSummary[]>(res),
  );
}

export function listMyProjects(): Promise<ProjectSummary[]> {
  return fetch(`${API_URL}/api/me/projects`, { credentials: "include", headers: devAuthHeaders() }).then((res) =>
    handleResponse<ProjectSummary[]>(res),
  );
}

export function joinProject(id: number | string): Promise<Project> {
  return fetch(`${API_URL}/api/projects/${id}/join`, {
    method: "POST",
    credentials: "include",
    headers: devAuthHeaders(),
  }).then((res) => handleResponse<Project>(res));
}

export function createProject(input: ProjectInput): Promise<Project> {
  return fetch(`${API_URL}/api/projects`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", ...devAuthHeaders() },
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

export function setGithubLabelFilter(id: number | string, labels: string[]): Promise<Project> {
  return fetch(`${API_URL}/api/projects/${id}/github/label-filter`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ labels }),
  }).then((res) => handleResponse<Project>(res));
}

export function listContributors(id: number | string): Promise<Contributor[]> {
  return fetch(`${API_URL}/api/projects/${id}/contributors`).then((res) => handleResponse<Contributor[]>(res));
}
