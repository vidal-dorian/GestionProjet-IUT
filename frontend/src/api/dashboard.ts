import { ApiError } from "./projects";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface HoursOverTimePoint {
  period: string;
  hours: number;
}

export interface HoursOverTime {
  granularity: "day" | "week";
  points: HoursOverTimePoint[];
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const message = body?.detail ?? "Une erreur est survenue.";
    throw new ApiError(response.status, message);
  }
  return response.json() as Promise<T>;
}

export function getHoursOverTime(projectId: number | string): Promise<HoursOverTime> {
  return fetch(`${API_URL}/api/projects/${projectId}/dashboard/hours-over-time`).then((res) =>
    handleResponse<HoursOverTime>(res),
  );
}
