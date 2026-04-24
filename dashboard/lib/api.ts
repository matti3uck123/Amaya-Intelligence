// Thin fetch wrapper. Deliberately not a heavy client — the API surface
// is ~6 endpoints and the dashboard is a short-lived session, so this
// stays ~100 lines and easy to grep.

import type {
  RatingAccepted,
  RatingListItem,
  RatingStatus,
} from "./types";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { Accept: "application/json", ...(init?.headers || {}) },
    cache: "no-store",
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* ignore parse errors */
    }
    throw new ApiError(res.status, `${res.status}: ${detail}`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export async function listRatings(): Promise<RatingListItem[]> {
  return request<RatingListItem[]>("/ratings");
}

export async function getRating(ratingId: string): Promise<RatingStatus> {
  return request<RatingStatus>(
    `/ratings/${encodeURIComponent(ratingId)}`,
  );
}

export async function deleteRating(ratingId: string): Promise<void> {
  await request<void>(`/ratings/${encodeURIComponent(ratingId)}`, {
    method: "DELETE",
  });
}

export interface CreateRatingArgs {
  files: File[];
  company: string;
  sector?: string;
  notes?: string;
  ratingId?: string;
  seal?: boolean;
}

export async function createRatingFromUpload(
  args: CreateRatingArgs,
): Promise<RatingAccepted> {
  const fd = new FormData();
  fd.append("company", args.company);
  if (args.sector) fd.append("sector", args.sector);
  if (args.notes) fd.append("notes", args.notes);
  if (args.ratingId) fd.append("rating_id", args.ratingId);
  if (args.seal) fd.append("seal", "true");
  for (const f of args.files) fd.append("files", f, f.name);

  return request<RatingAccepted>("/ratings", {
    method: "POST",
    body: fd,
  });
}

export interface FromPathArgs {
  path: string;
  company: string;
  sector?: string;
  notes?: string;
  ratingId?: string;
  seal?: boolean;
}

export async function createRatingFromPath(
  args: FromPathArgs,
): Promise<RatingAccepted> {
  return request<RatingAccepted>("/ratings/from-path", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      path: args.path,
      company: args.company,
      sector: args.sector ?? "",
      notes: args.notes ?? "",
      rating_id: args.ratingId,
      seal: args.seal ?? false,
    }),
  });
}

export async function verifyRating(
  ratingId: string,
  ledgerPath: string,
): Promise<{ rating_id: string; verified: boolean }> {
  return request("/verify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rating_id: ratingId, ledger_path: ledgerPath }),
  });
}

export function eventsUrl(ratingId: string): string {
  return `${API_URL}/ratings/${encodeURIComponent(ratingId)}/events`;
}

export function pdfUrl(ratingId: string): string {
  return `${API_URL}/ratings/${encodeURIComponent(ratingId)}/pdf`;
}

export interface ResetDemoResult {
  dropped: string[];
  seeded: string[];
  seed_enabled: boolean;
}

export async function resetDemo(): Promise<ResetDemoResult> {
  return request<ResetDemoResult>("/demo/reset", { method: "POST" });
}

export { ApiError };
