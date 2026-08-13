import { ApiError } from "./projects";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface Member {
  id: number;
  name: string;
  project_id: number;
  created_at: string;
  total_hours: number;
}

export interface MemberInput {
  name: string;
  pin: string;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const message = body?.detail ?? "Une erreur est survenue.";
    throw new ApiError(response.status, message);
  }
  return response.json() as Promise<T>;
}

export function listMembers(projectId: number | string): Promise<Member[]> {
  return fetch(`${API_URL}/api/projects/${projectId}/members`).then((res) => handleResponse<Member[]>(res));
}

export function createMember(projectId: number | string, input: MemberInput): Promise<Member> {
  return fetch(`${API_URL}/api/projects/${projectId}/members`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  }).then((res) => handleResponse<Member>(res));
}

export function deleteMember(projectId: number | string, memberId: number): Promise<void> {
  return fetch(`${API_URL}/api/projects/${projectId}/members/${memberId}`, { method: "DELETE" }).then((res) => {
    if (!res.ok) throw new ApiError(res.status, "Impossible de retirer ce membre.");
  });
}
