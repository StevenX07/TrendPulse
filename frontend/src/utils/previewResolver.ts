import { fetchLivePreview } from "../api/client";
import type { WeeklySongTrend } from "../types/trends";

export interface ResolvedPreview {
  url: string;
  source: string;
}

interface CachedPreview extends ResolvedPreview {
  fetchedAt: number;
}

const sessionPreviewCache = new Map<string, CachedPreview>();
const SESSION_CACHE_TTL_MS = 10 * 60 * 1000;

function normalizeText(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/\([^)]*\)|\[[^\]]*\]/g, " ")
    .replace(/\b(official|music|video|lyric|lyrics|audio|m\/v|mv|feat\.?|ft\.?)\b/gi, " ")
    .replace(/[^a-z0-9\u0400-\u04ff\u3040-\u30ff\u4e00-\u9fff\uac00-\ud7af]+/gi, " ")
    .trim();
}

function tokenize(value: string): string[] {
  return normalizeText(value)
    .split(/\s+/)
    .filter((tok) => tok.length >= 2);
}

function primaryArtist(artist: string): string {
  return artist
    .split(/\s*(?:,|&|feat\.?|ft\.?| x |\/|\+)\s*/i)[0]
    .trim();
}

function matchesSongCandidate(
  targetTitle: string,
  targetArtist: string,
  candTitle: string,
  candArtist: string,
): boolean {
  const normTargetTitle = normalizeText(targetTitle);
  const normCandTitle = normalizeText(candTitle);
  if (!normTargetTitle || !normCandTitle) return false;

  const titleMatch =
    normTargetTitle === normCandTitle ||
    normCandTitle.includes(normTargetTitle) ||
    normTargetTitle.includes(normCandTitle) ||
    (() => {
      const aTokens = tokenize(targetTitle);
      const bSet = new Set(tokenize(candTitle));
      if (aTokens.length === 0) return false;
      const hits = aTokens.filter((t) => bSet.has(t)).length;
      return hits / aTokens.length >= 0.6;
    })();

  if (!titleMatch) return false;

  const pArtist = normalizeText(primaryArtist(targetArtist));
  const cArtist = normalizeText(candArtist);
  if (!pArtist || pArtist === "desconocido" || pArtist === "unknown" || pArtist === "various artists") {
    return true;
  }
  if (cArtist.includes(pArtist) || pArtist.includes(cArtist)) {
    return true;
  }
  const artistTokens = tokenize(pArtist);
  const candArtistTokens = new Set(tokenize(cArtist));
  return artistTokens.some((tok) => candArtistTokens.has(tok));
}

/**
 * Checks whether a preview URL is a signed Deezer CDN link whose HMAC expiry
 * (`hdnea=exp=<unix_ts>`) has passed or is about to expire within 20 seconds.
 * Apple iTunes `.m4a` URLs are non-expiring and always return false.
 */
export function isPreviewUrlExpired(url?: string | null): boolean {
  if (!url) return false;
  const lower = url.toLowerCase();
  if (!lower.includes("dzcdn.net") && !lower.includes("hdnea=")) {
    return false;
  }
  let decoded = url;
  try {
    decoded = decodeURIComponent(url);
  } catch {
    // keep raw string
  }
  const match = /(?:^|[?&=~])exp=(\d{9,12})/i.exec(decoded);
  if (!match) {
    return false;
  }
  const expUnix = Number(match[1]);
  if (!Number.isFinite(expUnix)) return false;
  return Date.now() / 1000 >= expUnix - 20;
}

function fetchJsonp<T = Record<string, unknown>>(url: string, timeoutMs = 4500): Promise<T | null> {
  return new Promise((resolve) => {
    if (typeof document === "undefined") {
      resolve(null);
      return;
    }
    const cbName = `__tpJsonp_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
    const script = document.createElement("script");
    let settled = false;

    const cleanup = () => {
      if ((window as unknown as Record<string, unknown>)[cbName]) {
        delete (window as unknown as Record<string, unknown>)[cbName];
      }
      if (script.parentNode) {
        script.parentNode.removeChild(script);
      }
    };

    const timer = window.setTimeout(() => {
      if (settled) return;
      settled = true;
      cleanup();
      resolve(null);
    }, timeoutMs);

    (window as unknown as Record<string, unknown>)[cbName] = (payload: T) => {
      if (settled) return;
      settled = true;
      window.clearTimeout(timer);
      cleanup();
      resolve(payload);
    };

    script.onerror = () => {
      if (settled) return;
      settled = true;
      window.clearTimeout(timer);
      cleanup();
      resolve(null);
    };

    const sep = url.includes("?") ? "&" : "?";
    script.src = `${url}${sep}output=jsonp&callback=${encodeURIComponent(cbName)}`;
    script.async = true;
    document.head.appendChild(script);
  });
}

async function resolveFromItunesCors(title: string, artist: string): Promise<ResolvedPreview | null> {
  const cleanTitle = normalizeText(title) || title;
  const cleanArtist = normalizeText(primaryArtist(artist));
  const query = cleanArtist && cleanArtist !== "desconocido"
    ? `${cleanTitle} ${cleanArtist}`
    : cleanTitle;
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), 4500);
  try {
    const resp = await fetch(
      `https://itunes.apple.com/search?term=${encodeURIComponent(query)}&entity=song&media=music&limit=6`,
      { signal: controller.signal },
    );
    if (!resp.ok) return null;
    const data = (await resp.json()) as {
      results?: Array<{
        trackName?: string;
        artistName?: string;
        previewUrl?: string;
      }>;
    };
    const results = data.results || [];
    for (const item of results) {
      if (!item.previewUrl) continue;
      if (
        matchesSongCandidate(
          title,
          artist,
          item.trackName || "",
          item.artistName || "",
        )
      ) {
        return { url: item.previewUrl, source: "itunes_live" };
      }
    }
    return null;
  } catch {
    return null;
  } finally {
    window.clearTimeout(timer);
  }
}

async function resolveFromDeezerJsonp(song: WeeklySongTrend): Promise<ResolvedPreview | null> {
  const trackIdMatch = /\/track\/(\d+)/.exec(song.deezer_url || "");
  if (trackIdMatch) {
    const data = await fetchJsonp<{ preview?: string }>(
      `https://api.deezer.com/track/${trackIdMatch[1]}`,
    );
    if (data?.preview && !isPreviewUrlExpired(data.preview)) {
      return { url: data.preview, source: "deezer_live" };
    }
  }

  const cleanTitle = normalizeText(song.title) || song.title;
  const cleanArtist = normalizeText(primaryArtist(song.artist));
  const q = cleanArtist && cleanArtist !== "desconocido"
    ? `${cleanTitle} ${cleanArtist}`
    : cleanTitle;
  const searchData = await fetchJsonp<{
    data?: Array<{
      title?: string;
      preview?: string;
      artist?: { name?: string };
    }>;
  }>(`https://api.deezer.com/search?q=${encodeURIComponent(q)}&limit=5`);

  for (const item of searchData?.data || []) {
    if (!item.preview || isPreviewUrlExpired(item.preview)) continue;
    if (
      matchesSongCandidate(
        song.title,
        song.artist,
        item.title || "",
        item.artist?.name || "",
      )
    ) {
      return { url: item.preview, source: "deezer_live" };
    }
  }
  return null;
}

/**
 * Resolves a playable, non-expired 30s audio preview URL for a song.
 * Uses local FastAPI `/api/preview` when available, and falls back to
 * direct iTunes CORS + Deezer JSONP lookups so static GitHub Pages builds
 * also refresh expired signed Deezer preview links seamlessly.
 */
export async function resolveFreshPreview(
  song: WeeklySongTrend,
  isLocalApi: boolean,
): Promise<ResolvedPreview | null> {
  const cached = sessionPreviewCache.get(song.song_key);
  if (
    cached &&
    Date.now() - cached.fetchedAt < SESSION_CACHE_TTL_MS &&
    !isPreviewUrlExpired(cached.url)
  ) {
    return { url: cached.url, source: cached.source };
  }

  if (isLocalApi) {
    try {
      const apiRes = await fetchLivePreview(
        song.title,
        song.artist,
        song.deezer_url || undefined,
      );
      if (apiRes?.preview_url && !isPreviewUrlExpired(apiRes.preview_url)) {
        const resolved = {
          url: apiRes.preview_url,
          source: apiRes.preview_source || "live",
        };
        sessionPreviewCache.set(song.song_key, { ...resolved, fetchedAt: Date.now() });
        return resolved;
      }
    } catch {
      // Fall back to direct browser resolution
    }
  }

  const itunesMatch = await resolveFromItunesCors(song.title, song.artist);
  if (itunesMatch) {
    sessionPreviewCache.set(song.song_key, { ...itunesMatch, fetchedAt: Date.now() });
    return itunesMatch;
  }

  const deezerMatch = await resolveFromDeezerJsonp(song);
  if (deezerMatch) {
    sessionPreviewCache.set(song.song_key, { ...deezerMatch, fetchedAt: Date.now() });
    return deezerMatch;
  }

  return null;
}
