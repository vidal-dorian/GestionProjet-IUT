import { ApiError } from "./projects";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface SessionMember {
  id: number;
  name: string;
  project_id: number;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const message = body?.detail ?? "Une erreur est survenue.";
    throw new ApiError(response.status, message);
  }
  return response.json() as Promise<T>;
}

export function login(
  projectId: number | string,
  memberId: number,
  pin: string,
): Promise<SessionMember> {
  return fetch(`${API_URL}/api/projects/${projectId}/members/${memberId}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ pin }),
  }).then((res) => handleResponse<SessionMember>(res));
}

export function me(): Promise<SessionMember> {
  return fetch(`${API_URL}/api/auth/me`, { credentials: "include" }).then((res) =>
    handleResponse<SessionMember>(res),
  );
}

export function logout(): Promise<void> {
  return fetch(`${API_URL}/api/auth/logout`, { method: "POST", credentials: "include" }).then((res) => {
    if (!res.ok) throw new ApiError(res.status, "Impossible de se déconnecter.");
  });
}
