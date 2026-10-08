import { devAuthHeaders } from "./authHeaders";
import { ApiError, extractErrorMessage } from "./projects";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface Account {
  id: number;
  email: string;
  display_name: string | null;
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

export function updateMyDisplayName(displayName: string): Promise<Account> {
  return fetch(`${API_URL}/api/me`, {
    method: "PUT",
    credentials: "include",
    headers: { "Content-Type": "application/json", ...devAuthHeaders() },
    body: JSON.stringify({ display_name: displayName }),
  }).then((res) => handleResponse<Account>(res));
}

/** Nom affiché d'un compte : son nom s'il l'a renseigné, sinon son e-mail. */
export function accountLabel(account: { email: string; display_name?: string | null }): string {
  return account.display_name?.trim() || account.email;
}
