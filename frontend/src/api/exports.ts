import { devAuthHeaders } from "./authHeaders";
import { ApiError } from "./projects";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function filenameFromResponse(response: Response, fallback: string): string {
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = /filename="?([^"]+)"?/.exec(disposition);
  return match ? match[1] : fallback;
}

export async function downloadMyTimeEntriesExport(projectId: number | string): Promise<void> {
  const response = await fetch(`${API_URL}/api/projects/${projectId}/time-entries/export`, {
    credentials: "include",
    headers: devAuthHeaders(),
  });
  if (!response.ok) {
    throw new ApiError(response.status, "Impossible d'exporter vos données pour le moment.");
  }
  const blob = await response.blob();
  triggerDownload(blob, filenameFromResponse(response, "export.xlsx"));
}

export async function downloadProjectExport(projectId: number | string): Promise<void> {
  const response = await fetch(`${API_URL}/api/projects/${projectId}/export`, {
    credentials: "include",
    headers: devAuthHeaders(),
  });
  if (!response.ok) {
    throw new ApiError(response.status, "Impossible d'exporter les données du projet pour le moment.");
  }
  const blob = await response.blob();
  triggerDownload(blob, filenameFromResponse(response, "export.xlsx"));
}
