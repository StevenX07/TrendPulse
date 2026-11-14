"""Zero-cost ($0.00) music chart and preview enrichment connectors for TrendPulse."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
from bs4 import BeautifulSoup
from ytmusicapi import YTMusic

from .normalization import (
    clean_artist_name,
    clean_track_title,
    make_song_key,
    make_title_only_key,
    strip_accents,
)

logger = logging.getLogger(__name__)

USER_AGENT = "TrendPulse/2.0 (+https://github.com/trendpulse)"
REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def _parse_int(text: str) -> Optional[int]:
    cleaned = re.sub(r"[^0-9\-+]", "", (text or "").strip())
    if not cleaned or cleaned in ("-", "+"):
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


def _parse_float(text: str) -> Optional[float]:
    cleaned = re.sub(r"[^0-9.\-+]", "", (text or "").strip())
    if not cleaned or cleaned in ("-", "+", "."):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _calc_growth_pct(current: Optional[int], delta: Optional[int]) -> Optional[float]:
    if current is None or delta is None:
        return None
    baseline = current - delta
    if baseline <= 0:
        return None
    return round((delta / baseline) * 100.0, 1)


def _split_artist_title(raw_text: str) -> Tuple[str, str]:
    text = (raw_text or "").strip()
    if " - " in text:
        left, right = text.split(" - ", 1)
        return clean_artist_name(left), clean_track_title(right)
    if "|" in text:
        head = text.split("|", 1)[0].strip()
        if ":" in head:
            art, trk = head.split(":", 1)
            return clean_artist_name(art), clean_track_title(trk)
        return "YouTube Trending", clean_track_title(head)
    return "", clean_track_title(text)


# ---------------------------------------------------------------------------
# Deterministic HTML / JSON Parsers (unit-tested with fixtures)
# ---------------------------------------------------------------------------


def parse_kworb_spotify_weekly_html(html: str, limit: int = 200) -> List[Dict[str, Any]]:
    """Parse Kworb Spotify Global Weekly HTML (`Pos, P+, Artist and Title, Wks, Pk, (x?), Streams, Streams+, Total`)."""
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if not table:
        return []

    rows_out: List[Dict[str, Any]] = []
    for tr in table.select("tr"):
        cols = tr.find_all("td")
        if len(cols) < 9:
            continue
        rank = _parse_int(cols[0].get_text(strip=True))
        if rank is None:
            continue

        rank_change = cols[1].get_text(strip=True) or "="
        cell = cols[2]
        links = cell.find_all("a")
        artist = links[0].get_text(strip=True) if len(links) >= 1 else ""
        title = links[1].get_text(strip=True) if len(links) >= 2 else ""

        spotify_id = ""
        for a_tag in links:
            m_id = re.search(r"/track/([A-Za-z0-9]{15,30})", a_tag.get("href") or "")
            if m_id:
                spotify_id = m_id.group(1)
                break

        if not title or not artist:
            parsed_artist, parsed_title = _split_artist_title(cell.get_text(" ", strip=True))
            artist = artist or parsed_artist
            title = title or parsed_title

        if not title or not artist:
            continue

        weeks = _parse_int(cols[3].get_text(strip=True))
        peak = _parse_int(cols[4].get_text(strip=True))
        streams = _parse_int(cols[6].get_text(strip=True))
        streams_delta = _parse_int(cols[7].get_text(strip=True))

        c_title = clean_track_title(title)
        c_artist = clean_artist_name(artist)
        rows_out.append(
            {
                "rank": rank,
                "rank_change": rank_change,
                "title": c_title,
                "artist": c_artist,
                "song_key": make_song_key(c_title, c_artist),
                "title_key": make_title_only_key(c_title),
                "weeks_on_chart": weeks,
                "peak_rank": peak,
                "weekly_streams": streams,
                "weekly_delta": streams_delta,
                "weekly_growth_pct": _calc_growth_pct(streams, streams_delta),
                "spotify_url": f"https://open.spotify.com/track/{spotify_id}" if spotify_id else "",
            }
        )
        if len(rows_out) >= limit:
            break

    return rows_out


def parse_kworb_spotify_daily_html(html: str, limit: int = 200) -> List[Dict[str, Any]]:
    """Parse Kworb Spotify Daily HTML (`Pos, P+, Artist and Title, Days, Pk, (x?), Streams, Streams+, 7Day, 7Day+, Total`)."""
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", id="spotifydaily") or soup.find("table")
    if not table:
        return []

    rows_out: List[Dict[str, Any]] = []
    for tr in table.select("tr"):
        cols = tr.find_all("td")
        if len(cols) < 10:
            continue
        rank = _parse_int(cols[0].get_text(strip=True))
        if rank is None:
            continue

        rank_change = cols[1].get_text(strip=True) or "="
        cell = cols[2]
        links = cell.find_all("a")
        artist = links[0].get_text(strip=True) if len(links) >= 1 else ""
        title = links[1].get_text(strip=True) if len(links) >= 2 else ""

        spotify_id = ""
        for a_tag in links:
            m_id = re.search(r"/track/([A-Za-z0-9]{15,30})", a_tag.get("href") or "")
            if m_id:
                spotify_id = m_id.group(1)
                break

        if not title or not artist:
            parsed_artist, parsed_title = _split_artist_title(cell.get_text(" ", strip=True))
            artist = artist or parsed_artist
            title = title or parsed_title

        if not title or not artist:
            continue

        daily_streams = _parse_int(cols[6].get_text(strip=True))
        seven_day = _parse_int(cols[8].get_text(strip=True))
        seven_day_delta = _parse_int(cols[9].get_text(strip=True))
        c_title = clean_track_title(title)
        c_artist = clean_artist_name(artist)

        rows_out.append(
            {
                "rank": rank,
                "rank_change": rank_change,
                "title": c_title,
                "artist": c_artist,
                "song_key": make_song_key(c_title, c_artist),
                "title_key": make_title_only_key(c_title),
                "daily_streams": daily_streams,
                "seven_day_streams": seven_day,
                "seven_day_delta": seven_day_delta,
                "seven_day_growth_pct": _calc_growth_pct(seven_day, seven_day_delta),
                "spotify_url": f"https://open.spotify.com/track/{spotify_id}" if spotify_id else "",
            }
        )
        if len(rows_out) >= limit:
            break

    return rows_out


def parse_kworb_youtube_weekly_html(html: str, limit: int = 200) -> List[Dict[str, Any]]:
    """Parse Kworb YouTube Weekly HTML (`Pos, P+, Video, Wks, Pk, (x?), Views, Views+`)."""
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if not table:
        return []

    rows_out: List[Dict[str, Any]] = []
    for tr in table.select("tr"):
        cols = tr.find_all("td")
        if len(cols) < 7:
            continue
        rank = _parse_int(cols[0].get_text(strip=True))
        if rank is None:
            continue

        rank_change = cols[1].get_text(strip=True) or "="
        cell = cols[2]
        raw_text = cell.get_text(" ", strip=True)
        a_tag = cell.find("a")
        yt_id = ""
        if a_tag and a_tag.get("href"):
            m_vid = re.search(r"(?:video/|watch\?v=)([A-Za-z0-9_-]{11})", a_tag["href"])
            if m_vid:
                yt_id = m_vid.group(1)

        artist, title = _split_artist_title(raw_text)
        if not title:
            continue

        weeks = _parse_int(cols[3].get_text(strip=True))
        views = _parse_int(cols[6].get_text(strip=True))
        views_delta = _parse_int(cols[7].get_text(strip=True)) if len(cols) > 7 else None

        rows_out.append(
            {
                "rank": rank,
                "rank_change": rank_change,
                "title": title,
                "artist": artist or "YouTube Trending",
                "song_key": make_song_key(title, artist),
                "title_key": make_title_only_key(title),
                "weeks_on_chart": weeks,
                "weekly_views": views,
                "weekly_delta": views_delta,
                "weekly_growth_pct": _calc_growth_pct(views, views_delta),
                "youtube_video_id": yt_id,
                "youtube_url": f"https://www.youtube.com/watch?v={yt_id}" if yt_id else "",
            }
        )
        if len(rows_out) >= limit:
            break

    return rows_out


def parse_kworb_apple_music_html(html: str, limit: int = 200) -> List[Dict[str, Any]]:
    """Parse Kworb Worldwide Apple Music Songs chart (`Pos, P+, Artist and Title, Days, Pk, (x?), Pts, Pts+, TPts, ...`)."""
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if not table:
        return []

    rows_out: List[Dict[str, Any]] = []
    for tr in table.select("tr"):
        cols = tr.find_all("td")
        if len(cols) < 8:
            continue
        rank = _parse_int(cols[0].get_text(strip=True))
        if rank is None:
            continue

        rank_change = cols[1].get_text(strip=True) or "="
        raw_text = cols[2].get_text(" ", strip=True)
        artist, title = _split_artist_title(raw_text)
        if not title or not artist:
            continue

        pts = _parse_int(cols[6].get_text(strip=True))
        pts_delta = _parse_int(cols[7].get_text(strip=True))
        rows_out.append(
            {
                "rank": rank,
                "rank_change": rank_change,
                "title": title,
                "artist": artist,
                "song_key": make_song_key(title, artist),
                "title_key": make_title_only_key(title),
                "points": pts,
                "points_delta": pts_delta,
            }
        )
        if len(rows_out) >= limit:
            break

    return rows_out


def parse_kworb_radio_shazam_html(html: str, limit: int = 150) -> List[Dict[str, Any]]:
    """Parse Kworb Radio & Shazam cross-chart (`Pos, P+, Artist and Title, Days, Pk, (x?), Aud, Aud+, ..., Shazam`)."""
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if not table:
        return []

    rows_out: List[Dict[str, Any]] = []
    for tr in table.select("tr"):
        cols = tr.find_all("td")
        if len(cols) < 14:
            continue
        rank = _parse_int(cols[0].get_text(strip=True))
        if rank is None:
            continue

        artist, title = _split_artist_title(cols[2].get_text(" ", strip=True))
        if not title or not artist:
            continue

        aud = _parse_float(cols[6].get_text(strip=True))
        aud_delta = _parse_float(cols[7].get_text(strip=True))
        shazam_rank = _parse_int(cols[13].get_text(strip=True))
        rows_out.append(
            {
                "radio_rank": rank,
                "title": title,
                "artist": artist,
                "song_key": make_song_key(title, artist),
                "title_key": make_title_only_key(title),
                "radio_audience_m": aud,
                "radio_audience_delta": aud_delta,
                "shazam_rank": shazam_rank,
            }
        )
        if len(rows_out) >= limit:
            break

    return rows_out


def parse_itunes_rss_json(payload: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
    """Parse Apple iTunes RSS Top Songs feed with direct 30s AAC preview URLs and genres."""
    entries = (payload.get("feed") or {}).get("entry") or []
    if isinstance(entries, dict):
        entries = [entries]

    rows_out: List[Dict[str, Any]] = []
    for idx, entry in enumerate(entries[:limit], start=1):
        if not isinstance(entry, dict):
            continue
        raw_title = str((entry.get("im:name") or {}).get("label") or "").strip()
        raw_artist = str((entry.get("im:artist") or {}).get("label") or "").strip()
        if not raw_title or not raw_artist:
            continue

        imgs = entry.get("im:image") or []
        cover = ""
        if isinstance(imgs, list) and imgs:
            cover = str((imgs[-1] or {}).get("label") or "").replace("170x170bb", "500x500bb").replace("100x100bb", "500x500bb")

        preview = ""
        apple_url = ""
        links = entry.get("link") or []
        if isinstance(links, dict):
            links = [links]
        for lnk in links:
            attrs = (lnk or {}).get("attributes") or {}
            href = str(attrs.get("href") or "")
            if not href:
                continue
            if attrs.get("rel") == "enclosure" or attrs.get("im:assetType") == "preview":
                preview = href
            elif attrs.get("rel") == "alternate":
                apple_url = href

        genre = str(((entry.get("category") or {}).get("attributes") or {}).get("label") or "")
        title = clean_track_title(raw_title)
        artist = clean_artist_name(raw_artist)
        rows_out.append(
            {
                "rank": idx,
                "title": title,
                "artist": artist,
                "song_key": make_song_key(title, artist),
                "title_key": make_title_only_key(title),
                "cover_url": cover,
                "preview_url": preview,
                "genre": genre,
                "apple_music_url": apple_url,
            }
        )
    return rows_out


def parse_deezer_chart_json(payload: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
    """Parse Deezer `/chart/0/tracks` response."""
    data = payload.get("data") or []
    rows_out: List[Dict[str, Any]] = []
    for idx, r in enumerate(data[:limit], start=1):
        if not isinstance(r, dict):
            continue
        raw_title = str(r.get("title_short") or r.get("title") or "").strip()
        raw_artist = str((r.get("artist") or {}).get("name") or "").strip()
        if not raw_title or not raw_artist:
            continue

        album = r.get("album") or {}
        title = clean_track_title(raw_title)
        artist = clean_artist_name(raw_artist)
        rows_out.append(
            {
                "rank": idx,
                "deezer_id": r.get("id"),
                "deezer_rank": r.get("rank"),
                "title": title,
                "artist": artist,
                "song_key": make_song_key(title, artist),
                "title_key": make_title_only_key(title),
                "duration_sec": r.get("duration"),
                "preview_url": str(r.get("preview") or ""),
                "cover_url": str(album.get("cover_big") or album.get("cover_medium") or ""),
                "deezer_url": str(r.get("link") or ""),
            }
        )
    return rows_out


def parse_billboard_hot100_json(payload: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
    """Parse Billboard Hot 100 community JSON mirror (`mhollingshead/billboard-hot-100`)."""
    data = payload.get("data") or []
    rows_out: List[Dict[str, Any]] = []
    for row in data[:limit]:
        if not isinstance(row, dict):
            continue
        raw_title = str(row.get("song") or "").strip()
        raw_artist = str(row.get("artist") or "").strip()
        rank = _parse_int(str(row.get("this_week") or ""))
        if not raw_title or not raw_artist or rank is None:
            continue

        title = clean_track_title(raw_title)
        artist = clean_artist_name(raw_artist)
        rows_out.append(
            {
                "rank": rank,
                "last_week": row.get("last_week"),
                "peak": row.get("peak_position"),
                "weeks": row.get("weeks_on_chart"),
                "title": title,
                "artist": artist,
                "song_key": make_song_key(title, artist),
                "title_key": make_title_only_key(title),
            }
        )
    return rows_out


# ---------------------------------------------------------------------------
# Async Network Fetchers + Enrichment Cache
# ---------------------------------------------------------------------------


async def _fetch_text(client: httpx.AsyncClient, url: str) -> str:
    resp = await client.get(url, headers=REQUEST_HEADERS)
    resp.raise_for_status()
    return resp.text


async def _fetch_json(client: httpx.AsyncClient, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    resp = await client.get(url, params=params, headers={"User-Agent": USER_AGENT})
    resp.raise_for_status()
    return resp.json()


async def fetch_ytmusic_global_charts(limit: int = 100) -> List[Dict[str, Any]]:
    """Fetch unauthenticated YouTube Music global chart playlist via `ytmusicapi`."""

    def _sync() -> List[Dict[str, Any]]:
        yt = YTMusic()
        charts = yt.get_charts(country="ZZ")
        candidate_tracks: List[Dict[str, Any]] = []
        playlist_ids: List[str] = []

        for section_key in ("songs", "videos", "trending"):
            sec = charts.get(section_key)
            if isinstance(sec, dict) and isinstance(sec.get("items"), list):
                sec_list = sec["items"]
            elif isinstance(sec, list):
                sec_list = sec
            else:
                continue

            for entry in sec_list:
                if not isinstance(entry, dict):
                    continue
                if entry.get("playlistId") and not entry.get("videoId"):
                    playlist_ids.append(str(entry["playlistId"]))
                elif entry.get("videoId") or entry.get("title"):
                    candidate_tracks.append(entry)

        for pid in playlist_ids[:2]:
            try:
                pl = yt.get_playlist(pid, limit=limit)
                for tr in pl.get("tracks") or []:
                    if isinstance(tr, dict):
                        candidate_tracks.append(tr)
            except Exception as exc:
                logger.debug("ytmusic playlist %s skipped: %s", pid, exc)

        out: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for entry in candidate_tracks:
            raw_title = str(entry.get("title") or "").strip()
            vid = str(entry.get("videoId") or "").strip()
            artists = entry.get("artists") or []
            raw_artist = (
                str(artists[0].get("name") or "")
                if artists and isinstance(artists[0], dict)
                else ""
            )
            if not raw_title or not vid:
                continue
            title = clean_track_title(raw_title)
            artist = clean_artist_name(raw_artist) or "YouTube Artist"
            key = make_song_key(title, artist)
            if key in seen:
                continue
            seen.add(key)

            thumbs = entry.get("thumbnails") or []
            thumb = str(thumbs[-1].get("url") or "") if thumbs and isinstance(thumbs[-1], dict) else ""
            out.append(
                {
                    "rank": len(out) + 1,
                    "title": title,
                    "artist": artist,
                    "song_key": key,
                    "title_key": make_title_only_key(title),
                    "youtube_video_id": vid,
                    "youtube_url": f"https://www.youtube.com/watch?v={vid}",
                    "cover_url": thumb,
                }
            )
            if len(out) >= limit:
                break
        return out

    return await asyncio.to_thread(_sync)


async def fetch_all_free_sources(chart_limit: int = 200) -> Dict[str, Any]:
    """Fetch all zero-cost global music trend sources concurrently with fault isolation."""
    results: Dict[str, Any] = {
        "spotify_weekly": [],
        "spotify_daily": [],
        "youtube_weekly": [],
        "ytmusic_charts": [],
        "apple_music": [],
        "itunes_rss": [],
        "deezer_chart": [],
        "billboard_hot100": [],
        "radio_shazam": [],
        "statuses": [],
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(18.0, connect=8.0), follow_redirects=True) as client:

        async def run_safe(key: str, label: str, coro: Any) -> Tuple[str, str, str, Any, str]:
            try:
                data = await coro
                return key, label, "ok" if data else "error", data, "" if data else "Respuesta vacía"
            except Exception as exc:
                logger.warning("Free source '%s' failed: %s", key, exc)
                return key, label, "error", [], f"{type(exc).__name__}: {str(exc)[:100]}"

        async def _itunes_multi() -> List[Dict[str, Any]]:
            countries = ("us", "gb", "mx", "es", "br", "de")
            feeds = await asyncio.gather(
                *[
                    _fetch_json(client, f"https://itunes.apple.com/{cc}/rss/topsongs/limit=100/json")
                    for cc in countries
                ],
                return_exceptions=True,
            )
            combined: List[Dict[str, Any]] = []
            seen_keys: set[str] = set()
            for payload in feeds:
                if not isinstance(payload, dict):
                    continue
                for item in parse_itunes_rss_json(payload, limit=100):
                    if item["song_key"] not in seen_keys:
                        seen_keys.add(item["song_key"])
                        combined.append(item)
            return combined

        tasks = [
            run_safe(
                "spotify_weekly",
                "Spotify Global Weekly (Kworb)",
                _fetch_text(client, "https://kworb.net/spotify/country/global_weekly.html"),
            ),
            run_safe(
                "spotify_daily",
                "Spotify Global Daily (Kworb)",
                _fetch_text(client, "https://kworb.net/spotify/country/global_daily.html"),
            ),
            run_safe(
                "youtube_weekly",
                "YouTube Global Weekly (Kworb)",
                _fetch_text(client, "https://kworb.net/youtube/weekly/"),
            ),
            run_safe(
                "apple_music",
                "Apple Music Worldwide (Kworb)",
                _fetch_text(client, "https://kworb.net/apple_songs/"),
            ),
            run_safe(
                "radio_shazam",
                "Radio & Shazam Global (Kworb)",
                _fetch_text(client, "https://kworb.net/radio/"),
            ),
            run_safe(
                "deezer_chart",
                "Deezer Global Chart & Previews",
                _fetch_json(client, "https://api.deezer.com/chart/0/tracks?limit=100"),
            ),
            run_safe(
                "billboard_hot100",
                "Billboard Hot 100 Weekly",
                _fetch_json(client, "https://raw.githubusercontent.com/mhollingshead/billboard-hot-100/main/recent.json"),
            ),
            run_safe(
                "itunes_rss",
                "iTunes Top Songs RSS (US/GB/MX)",
                _itunes_multi(),
            ),
            run_safe(
                "ytmusic_charts",
                "YouTube Music Global (ytmusicapi)",
                fetch_ytmusic_global_charts(limit=100),
            ),
        ]

        raw_outcomes = await asyncio.gather(*tasks)

        parsers = {
            "spotify_weekly": lambda html: parse_kworb_spotify_weekly_html(html, limit=chart_limit),
            "spotify_daily": lambda html: parse_kworb_spotify_daily_html(html, limit=chart_limit),
            "youtube_weekly": lambda html: parse_kworb_youtube_weekly_html(html, limit=chart_limit),
            "apple_music": lambda html: parse_kworb_apple_music_html(html, limit=chart_limit),
            "radio_shazam": lambda html: parse_kworb_radio_shazam_html(html, limit=chart_limit),
            "deezer_chart": lambda js: parse_deezer_chart_json(js, limit=100),
            "billboard_hot100": lambda js: parse_billboard_hot100_json(js, limit=100),
        }

        for key, label, status, raw_data, note in raw_outcomes:
            parsed: List[Dict[str, Any]] = []
            if status == "ok":
                try:
                    parsed = parsers[key](raw_data) if key in parsers else raw_data
                except Exception as exc:
                    status = "error"
                    note = f"Parse error: {str(exc)[:90]}"
            if status == "ok" and not parsed:
                status = "error"
                note = note or "Sin resultados tras parsear"
            results[key] = parsed
            results["statuses"].append(
                {
                    "id": key,
                    "name": label,
                    "kind": "free",
                    "status": status,
                    "items_collected": len(parsed),
                    "cost_usd": 0.0,
                    "note": note,
                }
            )

    return results


# ---------------------------------------------------------------------------
# Per-song 30s Audio Preview, Artwork & BPM Enrichment (Deezer + iTunes)
# ---------------------------------------------------------------------------


def _is_ephemeral_preview(url: str) -> bool:
    """Return True for signed Deezer CDN preview links that expire quickly (`hdnea=exp=...`)."""
    low = (url or "").lower()
    return "dzcdn.net" in low or "hdnea=" in low


def _matches_artist_loosely(target_artist: str, candidate_artist: str) -> bool:
    t_tokens = set(re.findall(r"[a-z0-9]+", strip_accents(target_artist).lower()))
    c_tokens = set(re.findall(r"[a-z0-9]+", strip_accents(candidate_artist).lower()))
    if not t_tokens or not c_tokens:
        return True
    return bool(t_tokens & c_tokens)


def _matches_track_loosely(target_title: str, candidate_title: str) -> bool:
    t_tokens = set(re.findall(r"[a-z0-9]+", strip_accents(target_title).lower()))
    c_tokens = set(re.findall(r"[a-z0-9]+", strip_accents(candidate_title).lower()))
    if not t_tokens or not c_tokens:
        return True
    return bool(t_tokens & c_tokens)


def _load_meta_cache(cache_path: Optional[Path]) -> Dict[str, Dict[str, Any]]:
    if not cache_path or not cache_path.exists():
        return {}
    try:
        raw = json.loads(cache_path.read_text(encoding="utf-8"))
        now = time.time()
        cleaned: Dict[str, Dict[str, Any]] = {}
        for k, v in raw.items():
            if not isinstance(v, dict) or now - float(v.get("_ts", 0)) >= 7 * 86400:
                continue
            # Do not reuse expired signed Deezer preview URLs across runs
            if _is_ephemeral_preview(str(v.get("preview_url") or "")):
                v = {**v, "preview_url": "", "preview_source": ""}
            cleaned[k] = v
        return cleaned
    except Exception:
        return {}


def _save_meta_cache(cache_path: Optional[Path], data: Dict[str, Dict[str, Any]]) -> None:
    if not cache_path:
        return
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        logger.debug("Unable to save enrichment cache: %s", exc)


async def _lookup_deezer_meta(
    client: httpx.AsyncClient,
    title: str,
    artist: str,
    deezer_track_id: str = "",
) -> Dict[str, Any]:
    if deezer_track_id:
        try:
            tr = await client.get(f"https://api.deezer.com/track/{deezer_track_id}")
            if tr.status_code == 200:
                tj = tr.json()
                if tj.get("preview"):
                    album = tj.get("album") or {}
                    return {
                        "preview_url": str(tj.get("preview") or ""),
                        "preview_source": "deezer",
                        "cover_url": str(album.get("cover_big") or album.get("cover_medium") or ""),
                        "duration_sec": tj.get("duration"),
                        "bpm": float(tj["bpm"]) if tj.get("bpm") and float(tj["bpm"]) > 0 else None,
                        "deezer_rank": tj.get("rank"),
                        "deezer_url": str(tj.get("link") or ""),
                    }
        except Exception:
            pass

    queries = [f"{title} {artist}".strip()] if artist and artist != "YouTube Trending" else [title.strip()]
    if title.strip() and queries[0] != title.strip():
        queries.append(title.strip())

    for idx, q in enumerate(queries):
        try:
            r = await client.get("https://api.deezer.com/search", params={"q": q, "limit": 4})
            if r.status_code != 200:
                continue
            rows = r.json().get("data") or []
            chosen = None
            for cand in rows:
                cand_art = str((cand.get("artist") or {}).get("name") or "")
                cand_title = str(cand.get("title") or "")
                if _matches_artist_loosely(artist, cand_art) and _matches_track_loosely(title, cand_title):
                    chosen = cand
                    break
            if not chosen and idx == 0:
                for cand in rows:
                    if _matches_artist_loosely(artist, str((cand.get("artist") or {}).get("name") or "")):
                        chosen = cand
                        break
            if not chosen:
                continue

            track_id = chosen.get("id")
            bpm = None
            if track_id:
                tr = await client.get(f"https://api.deezer.com/track/{track_id}")
                if tr.status_code == 200:
                    tj = tr.json()
                    if tj.get("bpm") and float(tj["bpm"]) > 0:
                        bpm = float(tj["bpm"])
                    chosen = {**chosen, **tj}

            album = chosen.get("album") or {}
            return {
                "preview_url": str(chosen.get("preview") or ""),
                "preview_source": "deezer" if chosen.get("preview") else "",
                "cover_url": str(album.get("cover_big") or album.get("cover_medium") or ""),
                "duration_sec": chosen.get("duration"),
                "bpm": bpm,
                "deezer_rank": chosen.get("rank"),
                "deezer_url": str(chosen.get("link") or ""),
            }
        except Exception:
            continue
    return {}


async def _lookup_itunes_meta(client: httpx.AsyncClient, title: str, artist: str) -> Dict[str, Any]:
    has_real_artist = bool(artist and artist not in ("YouTube Trending", "YouTube Artist", "TikTok Trending", "Artista"))
    queries = [f"{artist} {title}".strip()] if has_real_artist else [title.strip()]
    if title.strip() and title.strip() not in queries:
        queries.append(title.strip())

    for q in queries:
        for attempt in range(2):
            try:
                r = await client.get(
                    "https://itunes.apple.com/search",
                    params={"term": q, "entity": "song", "limit": 5},
                )
                if r.status_code in (403, 429) and attempt == 0:
                    await asyncio.sleep(1.1)
                    continue
                if r.status_code != 200:
                    break
                rows = r.json().get("results") or []
                chosen = None
                for cand in rows:
                    c_art = str(cand.get("artistName") or "")
                    c_title = str(cand.get("trackName") or "")
                    if cand.get("previewUrl") and _matches_artist_loosely(artist, c_art) and _matches_track_loosely(title, c_title):
                        chosen = cand
                        break
                if not chosen and has_real_artist:
                    for cand in rows:
                        if cand.get("previewUrl") and _matches_artist_loosely(artist, str(cand.get("artistName") or "")):
                            chosen = cand
                            break
                if not chosen:
                    break
                artwork = str(chosen.get("artworkUrl100") or "").replace("100x100bb", "500x500bb")
                dur_ms = chosen.get("trackTimeMillis")
                return {
                    "preview_url": str(chosen.get("previewUrl") or ""),
                    "preview_source": "itunes" if chosen.get("previewUrl") else "",
                    "cover_url": artwork,
                    "genre": str(chosen.get("primaryGenreName") or ""),
                    "duration_sec": int(dur_ms / 1000) if dur_ms else None,
                    "apple_music_url": str(chosen.get("trackViewUrl") or ""),
                }
            except Exception:
                break
    return {}


async def resolve_live_preview(
    title: str,
    artist: str,
    deezer_url: str = "",
) -> Dict[str, str]:
    """Resolve a fresh non-expired preview URL on demand ($0.00): prefers permanent iTunes, falls back to Deezer."""
    dz_id = ""
    m = re.search(r"/track/(\d+)", deezer_url or "")
    if m:
        dz_id = m.group(1)

    async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=5.0)) as client:
        it = await _lookup_itunes_meta(client, title, artist)
        if it.get("preview_url"):
            return {"preview_url": it["preview_url"], "preview_source": "itunes"}
        dz = await _lookup_deezer_meta(client, title, artist, deezer_track_id=dz_id)
        if dz.get("preview_url"):
            return {"preview_url": dz["preview_url"], "preview_source": "deezer"}
    return {"preview_url": "", "preview_source": ""}


async def enrich_songs_metadata(
    songs: List[Dict[str, Any]],
    max_enrich: int = 230,
    cache_path: Optional[Path] = None,
) -> None:
    """Enrich kept songs in-place with permanent 30s audio previews (iTunes first), HD artwork, genres, and BPM."""
    cache = _load_meta_cache(cache_path)
    dz_sem = asyncio.Semaphore(8)
    it_sem = asyncio.Semaphore(2)

    # Include songs missing preview/cover OR holding an expiring signed Deezer link so iTunes upgrades them permanently
    targets = [
        s
        for s in songs[:max_enrich]
        if not s.get("preview_url") or _is_ephemeral_preview(s.get("preview_url", "")) or not s.get("cover_url")
    ]
    if not targets:
        return

    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=6.0)) as client:

        async def _enrich_one(song: Dict[str, Any]) -> None:
            key = song["song_key"]
            cached = cache.get(key)
            needs_permanent_preview = not cached or not cached.get("preview_url")

            if needs_permanent_preview:
                async with it_sem:
                    it = await _lookup_itunes_meta(client, song["title"], song["artist"])
                    await asyncio.sleep(0.14)

                dz: Dict[str, Any] = {}
                need_deezer = not song.get("bpm") or not song.get("deezer_url") or not it.get("preview_url") or not (it.get("cover_url") or song.get("cover_url"))
                if need_deezer:
                    dz_id_match = re.search(r"/track/(\d+)", str(song.get("deezer_url") or ""))
                    async with dz_sem:
                        dz = await _lookup_deezer_meta(
                            client,
                            song["title"],
                            song["artist"],
                            deezer_track_id=dz_id_match.group(1) if dz_id_match else "",
                        )

                # Always prefer permanent non-expiring iTunes preview when available
                chosen_preview = it.get("preview_url") or dz.get("preview_url") or ""
                chosen_source = "itunes" if it.get("preview_url") else (dz.get("preview_source") or "")

                merged = {
                    "_ts": time.time(),
                    "preview_url": chosen_preview,
                    "preview_source": chosen_source,
                    "cover_url": it.get("cover_url") or dz.get("cover_url") or "",
                    "duration_sec": dz.get("duration_sec") or it.get("duration_sec"),
                    "bpm": dz.get("bpm"),
                    "genre": it.get("genre") or "",
                    "deezer_rank": dz.get("deezer_rank"),
                    "deezer_url": dz.get("deezer_url") or "",
                    "apple_music_url": it.get("apple_music_url") or "",
                }
                # Cache permanent metadata safely; store Deezer preview only in live snapshot, not persistent cache
                cache_entry = {**merged}
                if _is_ephemeral_preview(cache_entry["preview_url"]):
                    cache_entry["preview_url"] = ""
                    cache_entry["preview_source"] = ""
                if cache_entry["preview_url"] or cache_entry["cover_url"] or cache_entry["deezer_url"]:
                    cache[key] = cache_entry
                cached = merged

            cached_url = str(cached.get("preview_url") or "")
            cached_src = str(cached.get("preview_source") or "")
            if cached_url:
                if not song.get("preview_url") or (
                    _is_ephemeral_preview(song.get("preview_url", "")) and not _is_ephemeral_preview(cached_url)
                ):
                    song["preview_url"] = cached_url
                    song["preview_source"] = cached_src or "itunes"
            if not song.get("cover_url") and cached.get("cover_url"):
                song["cover_url"] = cached["cover_url"]
            if not song.get("duration_sec") and cached.get("duration_sec"):
                song["duration_sec"] = cached["duration_sec"]
            if not song.get("bpm") and cached.get("bpm"):
                song["bpm"] = cached["bpm"]
            if cached.get("genre") and cached["genre"] not in song.get("genres", []):
                song.setdefault("genres", []).append(cached["genre"])
            if not song.get("deezer_rank") and cached.get("deezer_rank"):
                song["deezer_rank"] = cached["deezer_rank"]
            if not song.get("deezer_url") and cached.get("deezer_url"):
                song["deezer_url"] = cached["deezer_url"]
            if not song.get("apple_music_url") and cached.get("apple_music_url"):
                song["apple_music_url"] = cached["apple_music_url"]

        await asyncio.gather(*(_enrich_one(song) for song in targets), return_exceptions=True)

    _save_meta_cache(cache_path, cache)
