import type { HistoryIndex, WeeklySnapshot } from "../types/trends";

const BASE = import.meta.env.BASE_URL || "/";

function joinBase(relPath: string): string {
  const cleanBase = BASE.endsWith("/") ? BASE : `${BASE}/`;
  const cleanPath = relPath.replace(/^\/+/, "");
  return `${cleanBase}${cleanPath}`;
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      const err = await resp.json();
      if (err?.detail) detail = String(err.detail);
    } catch {
      // keep status text
    }
    throw new Error(detail);
  }
  return resp.json() as Promise<T>;
}

/**
 * Probe whether local FastAPI backend is active (true when running locally with start.ps1,
 * false when hosted statically on GitHub Pages).
 */
export async function checkLocalApiAvailable(): Promise<boolean> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), 1100);
  try {
    const resp = await fetch("/api/health", { signal: controller.signal });
    if (!resp.ok) return false;
    const contentType = resp.headers.get("content-type") || "";
    return contentType.includes("application/json");
  } catch {
    return false;
  } finally {
    window.clearTimeout(timer);
  }
}

export async function loadLatestSnapshot(isLocalApi: boolean): Promise<WeeklySnapshot> {
  if (isLocalApi) {
    try {
      return await fetchJson<WeeklySnapshot>("/api/snapshot");
    } catch {
      // Fallback to static JSON in public/data/
    }
  }
  return fetchJson<WeeklySnapshot>(joinBase(`data/latest.json?t=${Date.now()}`));
}

export async function loadHistoryIndex(isLocalApi: boolean): Promise<HistoryIndex> {
  if (isLocalApi) {
    try {
      return await fetchJson<HistoryIndex>("/api/history");
    } catch {
      // Fallback to static JSON
    }
  }
  try {
    return await fetchJson<HistoryIndex>(joinBase(`data/history.json?t=${Date.now()}`));
  } catch {
    return { updated_at: "", weeks: [] };
  }
}

export async function loadArchiveWeek(weekId: string, isLocalApi: boolean): Promise<WeeklySnapshot> {
  if (isLocalApi) {
    try {
      return await fetchJson<WeeklySnapshot>(`/api/archive/${encodeURIComponent(weekId)}`);
    } catch {
      // Fallback to static archive JSON
    }
  }
  return fetchJson<WeeklySnapshot>(joinBase(`data/archive/${encodeURIComponent(weekId)}.json`));
}

export interface LivePreviewResponse {
  preview_url: string | null;
  preview_source: string | null;
}

export async function fetchLivePreview(
  title: string,
  artist: string,
  deezerUrl?: string,
): Promise<LivePreviewResponse | null> {
  const params = new URLSearchParams({ title, artist });
  if (deezerUrl) {
    params.set("deezer_url", deezerUrl);
  }
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), 5500);
  try {
    const resp = await fetch(`/api/preview?${params.toString()}`, {
      signal: controller.signal,
    });
    if (!resp.ok) return null;
    return (await resp.json()) as LivePreviewResponse;
  } catch {
    return null;
  } finally {
    window.clearTimeout(timer);
  }
}
