import { devAuthHeaders } from "./authHeaders";
import { ApiError, extractErrorMessage } from "./projects";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface Account {
  id: number;
  email: string;
  is_admin: boolean;
  created_at: string;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const message = extractErrorMessage(body?.detail, response.status);
    throw new ApiError(response.status, message);
  }
  return response.json() as Promise<T>;
}

export function me(): Promise<Account> {
  return fetch(`${API_URL}/api/me`, { credentials: "include", headers: devAuthHeaders() }).then((res) =>
    handleResponse<Account>(res),
  );
}
