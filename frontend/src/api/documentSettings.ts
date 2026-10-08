import { devAuthHeaders } from "./authHeaders";
import { ApiError, extractErrorMessage } from "./projects";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export type LogoPosition = "left" | "right";

export interface DocumentSettings {
  footer: string;
  logos: LogoPosition[];
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const message = extractErrorMessage(body?.detail, response.status);
    throw new ApiError(response.status, message);
  }
  return response.json() as Promise<T>;
}

function settingsUrl(projectId: number | string): string {
  return `${API_URL}/api/projects/${projectId}/document-settings`;
}

export function getDocumentSettings(projectId: number | string): Promise<DocumentSettings> {
  return fetch(settingsUrl(projectId), { credentials: "include", headers: devAuthHeaders() }).then((res) =>
    handleResponse<DocumentSettings>(res),
  );
}

export function updateDocumentFooter(projectId: number | string, footer: string): Promise<DocumentSettings> {
  return fetch(settingsUrl(projectId), {
    method: "PUT",
    credentials: "include",
    headers: { "Content-Type": "application/json", ...devAuthHeaders() },
    body: JSON.stringify({ footer }),
  }).then((res) => handleResponse<DocumentSettings>(res));
}

/** Récupère le logo en blob (l'en-tête d'authentification de dev empêche un simple <img src>). */
export async function fetchLogoObjectUrl(projectId: number | string, position: LogoPosition): Promise<string> {
  const response = await fetch(`${settingsUrl(projectId)}/logos/${position}`, {
    credentials: "include",
    headers: devAuthHeaders(),
  });
  if (!response.ok) throw new ApiError(response.status, "Logo introuvable.");
  return URL.createObjectURL(await response.blob());
}

function readAsBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",", 2)[1] ?? "");
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

export async function uploadLogo(projectId: number | string, position: LogoPosition, file: File): Promise<DocumentSettings> {
  const data_base64 = await readAsBase64(file);
  return fetch(`${settingsUrl(projectId)}/logos/${position}`, {
    method: "PUT",
    credentials: "include",
    headers: { "Content-Type": "application/json", ...devAuthHeaders() },
    body: JSON.stringify({ data_base64 }),
  }).then((res) => handleResponse<DocumentSettings>(res));
}

export function deleteLogo(projectId: number | string, position: LogoPosition): Promise<void> {
  return fetch(`${settingsUrl(projectId)}/logos/${position}`, {
    method: "DELETE",
    credentials: "include",
    headers: devAuthHeaders(),
  }).then((res) => {
    if (!res.ok) throw new ApiError(res.status, "Impossible de supprimer ce logo.");
  });
}
