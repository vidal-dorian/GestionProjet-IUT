import type { Account } from "./auth";
import { devAuthHeaders } from "./authHeaders";
import { ApiError, type MembershipStatus } from "./projects";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface MembershipRequest {
  id: number;
  project_id: number;
  project_name: string;
  account_id: number;
  account_email: string;
  status: MembershipStatus;
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

export function listMembershipRequests(): Promise<MembershipRequest[]> {
  return fetch(`${API_URL}/api/admin/membership-requests`, {
    credentials: "include",
    headers: devAuthHeaders(),
  }).then((res) => handleResponse<MembershipRequest[]>(res));
}

export function approveMembershipRequest(id: number): Promise<MembershipRequest> {
  return fetch(`${API_URL}/api/admin/membership-requests/${id}/approve`, {
    method: "POST",
    credentials: "include",
    headers: devAuthHeaders(),
  }).then((res) => handleResponse<MembershipRequest>(res));
}

export function rejectMembershipRequest(id: number): Promise<MembershipRequest> {
  return fetch(`${API_URL}/api/admin/membership-requests/${id}/reject`, {
    method: "POST",
    credentials: "include",
    headers: devAuthHeaders(),
  }).then((res) => handleResponse<MembershipRequest>(res));
}

export function listProjectMembers(projectId: number | string): Promise<Account[]> {
  return fetch(`${API_URL}/api/admin/projects/${projectId}/members`, {
    credentials: "include",
    headers: devAuthHeaders(),
  }).then((res) => handleResponse<Account[]>(res));
}

export function removeProjectMember(projectId: number | string, accountId: number): Promise<void> {
  return fetch(`${API_URL}/api/admin/projects/${projectId}/members/${accountId}`, {
    method: "DELETE",
    credentials: "include",
    headers: devAuthHeaders(),
  }).then((res) => {
    if (!res.ok) throw new ApiError(res.status, "Impossible de retirer ce membre pour le moment.");
  });
}
