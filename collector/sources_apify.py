"""Apify multi-platform music trend connectors (TikTok, Instagram Reels, Shazam Global, Spotify Viral) with strict USD caps."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import httpx

from .models import SocialSampleVideo, SourceStatus
from .normalization import (
    clean_artist_name,
    clean_track_title,
    is_original_sound,
    make_song_key,
    make_title_only_key,
)

logger = logging.getLogger(__name__)

APIFY_BASE_URL = "https://api.apify.com/v2"

# Verified Pay-Per-Event Apify Actors (compatible with Apify Free Tier)
ACTOR_TIKTOK_HISTORY = "trendingtiktoksongs~tiktok-trending-sounds-history"
ACTOR_TIKTOK_EXPLORE = "s_actors~tiktok-trending-sounds-scraper"
ACTOR_IG_REELS = "trendingtiktoksongs~instagram-audio-history"
ACTOR_SHAZAM_CHARTS = "automation-lab~shazam-charts-scraper"
ACTOR_SPOTIFY_SCRAPER = "eduair94~spotify-scraper"

SPOTIFY_VIRAL_CHART_QUERY = "GLOBAL"

# Unit pricing constants (Apify FREE tier)
HISTORY_START_USD = 0.00005
HISTORY_PER_ROW_USD = 0.003

EXPLORE_START_USD = 0.001
EXPLORE_PER_100_VIDEOS_USD = 0.006
EXPLORE_PER_SOUND_USD = 0.00099

REELS_START_USD = 0.00005
REELS_PER_ROW_USD = 0.003

SHAZAM_START_USD = 0.005
SHAZAM_PER_TRACK_USD = 0.00036344

SPOTIFY_START_USD = 0.0
SPOTIFY_PER_ITEM_USD = 0.001


def estimate_apify_weekly_cost(
    history_max_rows: int = 100,
    explore_countries: int = 4,
    explore_sample_videos: int = 800,
    explore_max_sounds: int = 60,
    reels_max_rows: int = 60,
    shazam_max_items: int = 250,
    spotify_items: int = 74,
) -> Dict[str, Any]:
    """Return transparent weekly + monthly USD estimate across all 5 Apify actors."""
    history_est = round(HISTORY_START_USD + (history_max_rows * HISTORY_PER_ROW_USD), 4)
    explore_est = round(
        EXPLORE_START_USD
        + ((explore_countries * explore_sample_videos) / 100.0) * EXPLORE_PER_100_VIDEOS_USD
        + (explore_max_sounds * EXPLORE_PER_SOUND_USD),
        4,
    )
    reels_est = round(REELS_START_USD + (reels_max_rows * REELS_PER_ROW_USD), 4)
    shazam_est = round(SHAZAM_START_USD + (shazam_max_items * SHAZAM_PER_TRACK_USD), 4)
    spotify_est = round(SPOTIFY_START_USD + (spotify_items * SPOTIFY_PER_ITEM_USD), 4)

    weekly = round(history_est + explore_est + reels_est + shazam_est + spotify_est, 2)
    monthly_4w = round(weekly * 4, 2)
    monthly_5w = round(weekly * 5, 2)

    return {
        "estimated_usd": weekly,
        "monthly_4_weeks_usd": monthly_4w,
        "monthly_5_weeks_usd": monthly_5w,
        "breakdown": {
            "tiktok_history_usd": round(history_est, 3),
            "tiktok_explore_usd": round(explore_est, 3),
            "instagram_reels_usd": round(reels_est, 3),
            "shazam_charts_usd": round(shazam_est, 3),
            "spotify_viral_plays_usd": round(spotify_est, 3),
        },
        "formula": (
            f"TikTok 7D (~${history_est:.2f}) + TikTok 4 países (~${explore_est:.2f}) + "
            f"Instagram Reels (~${reels_est:.2f}) + Shazam Global/Viral (~${shazam_est:.2f}) + "
            f"Spotify Viral/Plays (~${spotify_est:.2f}) ≈ ${weekly:.2f}/sem (~${monthly_4w:.2f}/mes)"
        ),
    }


def _to_int(val: Any) -> Optional[int]:
    if val is None or val == "":
        return None
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return None


def _to_float(val: Any) -> Optional[float]:
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Deterministic Dataset Parsers
# ---------------------------------------------------------------------------


def parse_history_insights_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize `trendingtiktoksongs~tiktok-trending-sounds-history` rows."""
    by_sound: Dict[str, Dict[str, Any]] = {}

    for row in items:
        if not isinstance(row, dict):
            continue
        rec_type = str(row.get("record_type") or "").strip().lower()
        if rec_type and rec_type not in ("sound_insight", "sound_chart", ""):
            if "coverage" in rec_type or "summary" in rec_type:
                continue

        sound_id = str(row.get("sound_id") or "").strip()
        raw_title = str(row.get("title") or "").strip()
        raw_artist = str(row.get("artist") or "").strip()
        if not sound_id and not raw_title:
            continue

        has_music_links = bool(
            row.get("spotify_url") or row.get("apple_music_url") or row.get("youtube_music_url")
        )
        if not has_music_links and is_original_sound(raw_title, raw_artist, row.get("is_original_sound")):
            continue

        title = clean_track_title(raw_title)
        artist = clean_artist_name(raw_artist) or "TikTok Trending"
        if not title:
            continue

        song_key = make_song_key(title, artist)
        rank = _to_int(row.get("rank"))
        chart_type = str(row.get("chart_type") or "viral").lower()
        country = str(row.get("country") or "").upper()
        usage_count = _to_int(row.get("usage_count"))
        usage_change = _to_int(row.get("usage_change"))
        growth_pct = _to_float(row.get("usage_growth_pct"))
        rank_change = _to_int(row.get("rank_change"))

        samples: List[SocialSampleVideo] = []
        for ex in row.get("examples") or []:
            if not isinstance(ex, dict):
                continue
            v_url = str(ex.get("video_url") or ex.get("url") or "").strip()
            if not v_url:
                continue
            samples.append(
                SocialSampleVideo(
                    url=v_url,
                    creator=str(ex.get("creator_handle") or ex.get("author") or ""),
                    caption=str(ex.get("caption") or "")[:160],
                    plays=_to_int(ex.get("plays") or ex.get("play_count")) or 0,
                    likes=_to_int(ex.get("likes") or ex.get("digg_count")) or 0,
                    published_at=str(ex.get("published_at") or ""),
                )
            )

        existing = by_sound.get(song_key)
        candidate = {
            "song_key": song_key,
            "title_key": make_title_only_key(title),
            "title": title,
            "artist": artist,
            "tiktok_sound_id": sound_id,
            "tiktok_rank": rank,
            "tiktok_chart_type": chart_type,
            "tiktok_countries": [country] if country else [],
            "tiktok_usage_count": usage_count,
            "tiktok_7d_usage_change": usage_change,
            "tiktok_7d_growth_pct": round(growth_pct, 1) if growth_pct is not None else None,
            "tiktok_rank_change": rank_change,
            "tiktok_is_viral": chart_type == "viral" or (growth_pct is not None and growth_pct >= 25.0),
            "tiktok_is_commercial": row.get("is_commerce_music"),
            "duration_sec": _to_int(row.get("duration_seconds")),
            "cover_url": str(row.get("cover_url") or ""),
            "tiktok_sound_url": str(row.get("tiktok_url") or ""),
            "spotify_url": str(row.get("spotify_url") or ""),
            "apple_music_url": str(row.get("apple_music_url") or ""),
            "youtube_url": str(row.get("youtube_music_url") or ""),
            "tiktok_samples": [s.model_dump() for s in samples[:3]],
        }

        if not existing:
            by_sound[song_key] = candidate
        else:
            if country and country not in existing["tiktok_countries"]:
                existing["tiktok_countries"].append(country)
            if rank and (not existing["tiktok_rank"] or rank < existing["tiktok_rank"]):
                existing["tiktok_rank"] = rank
            if (usage_change or 0) > (existing.get("tiktok_7d_usage_change") or -10**9):
                existing["tiktok_7d_usage_change"] = usage_change
            if (growth_pct or 0.0) > (existing.get("tiktok_7d_growth_pct") or -10**9):
                existing["tiktok_7d_growth_pct"] = round(growth_pct, 1) if growth_pct is not None else None
            if chart_type == "viral":
                existing["tiktok_is_viral"] = True
                existing["tiktok_chart_type"] = "viral"
            if samples and not existing.get("tiktok_samples"):
                existing["tiktok_samples"] = candidate["tiktok_samples"]
            for f_name in ("spotify_url", "apple_music_url", "youtube_url", "cover_url", "tiktok_sound_url"):
                if not existing.get(f_name) and candidate.get(f_name):
                    existing[f_name] = candidate[f_name]

    return list(by_sound.values())


def parse_explore_sounds_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize `s_actors~tiktok-trending-sounds-scraper` multi-country rows."""
    by_sound: Dict[str, Dict[str, Any]] = {}

    for row in items:
        if not isinstance(row, dict):
            continue
        raw_title = str(row.get("musicTitle") or "").strip()
        raw_artist = str(row.get("musicAuthor") or "").strip()
        if not raw_title or is_original_sound(raw_title, raw_artist, row.get("musicIsOriginal")):
            continue

        title = clean_track_title(raw_title)
        artist = clean_artist_name(raw_artist) or "TikTok Trending"
        if not title:
            continue

        song_key = make_song_key(title, artist)
        country = str(row.get("country") or "").upper()
        position = _to_int(row.get("position"))
        prev_pos = _to_int(row.get("previousPosition"))
        rank_change = (prev_pos - position) if (position and prev_pos) else None
        videos_in_sample = _to_int(row.get("videosInSample")) or 0
        sample_plays = _to_int(row.get("samplePlays")) or 0
        sample_likes = _to_int(row.get("sampleLikes")) or 0

        samples: List[SocialSampleVideo] = []
        if row.get("topVideoUrl"):
            samples.append(
                SocialSampleVideo(
                    url=str(row.get("topVideoUrl") or ""),
                    creator=str(row.get("topVideoAuthor") or ""),
                    plays=_to_int(row.get("topVideoPlays")) or sample_plays,
                    likes=sample_likes,
                )
            )
        for v_url in (row.get("videoUrls") or [])[:2]:
            if v_url and v_url != row.get("topVideoUrl"):
                samples.append(SocialSampleVideo(url=str(v_url)))

        audio_url = str(row.get("audioFileUrl") or row.get("musicAudioUrl") or "").strip()
        candidate = {
            "song_key": song_key,
            "title_key": make_title_only_key(title),
            "title": title,
            "artist": artist,
            "tiktok_sound_id": str(row.get("musicId") or ""),
            "tiktok_rank": position,
            "tiktok_chart_type": "explore",
            "tiktok_countries": [country] if country else [],
            "tiktok_rank_change": rank_change,
            "tiktok_explore_videos": videos_in_sample,
            "tiktok_explore_plays": sample_plays,
            "tiktok_is_new": bool(row.get("isNew")),
            "tiktok_is_viral": bool(row.get("isNew")) or videos_in_sample >= 3,
            "tiktok_is_commercial": row.get("musicIsCommercial"),
            "tiktok_newest_age_days": _to_int(row.get("newestVideoAgeDays")),
            "duration_sec": _to_int(row.get("musicDurationSeconds")),
            "cover_url": str(row.get("musicCoverUrl") or ""),
            "preview_url": audio_url,
            "preview_source": "tiktok" if audio_url else "",
            "tiktok_sound_url": str(row.get("musicUrl") or ""),
            "tiktok_samples": [s.model_dump() for s in samples[:3]],
        }

        existing = by_sound.get(song_key)
        if not existing:
            by_sound[song_key] = candidate
        else:
            if country and country not in existing["tiktok_countries"]:
                existing["tiktok_countries"].append(country)
            existing["tiktok_explore_videos"] = (existing.get("tiktok_explore_videos") or 0) + videos_in_sample
            existing["tiktok_explore_plays"] = (existing.get("tiktok_explore_plays") or 0) + sample_plays
            if position and (not existing["tiktok_rank"] or position < existing["tiktok_rank"]):
                existing["tiktok_rank"] = position
            if bool(row.get("isNew")):
                existing["tiktok_is_new"] = True
            if not existing.get("preview_url") and audio_url:
                existing["preview_url"] = audio_url
                existing["preview_source"] = "tiktok"

    return list(by_sound.values())


def parse_instagram_reels_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize `trendingtiktoksongs~instagram-audio-history` rows with 7D growth & Reel examples."""
    by_sound: Dict[str, Dict[str, Any]] = {}

    for idx, row in enumerate(items, start=1):
        if not isinstance(row, dict):
            continue
        rec_type = str(row.get("record_type") or "").strip().lower()
        if rec_type and ("summary" in rec_type or "coverage" in rec_type):
            continue

        raw_title = str(row.get("title") or "").strip()
        raw_artist = str(row.get("artist") or "").strip()
        kind = str(row.get("kind") or "").strip().lower()
        if not raw_title or is_original_sound(raw_title, raw_artist, kind == "original"):
            continue
        if raw_title.lower().startswith("original audio"):
            continue

        title = clean_track_title(raw_title)
        artist = clean_artist_name(raw_artist) or "Instagram Reels"
        if not title:
            continue

        song_key = make_song_key(title, artist)
        native_rank = _to_int(row.get("native_rank")) or idx
        growth_7d_pct = _to_float(row.get("growth_7d_percent"))

        samples: List[SocialSampleVideo] = []
        for ex in row.get("examples") or []:
            if not isinstance(ex, dict):
                continue
            v_url = str(ex.get("reel_url") or ex.get("url") or "").strip()
            if not v_url:
                continue
            samples.append(
                SocialSampleVideo(
                    url=v_url,
                    creator=str(ex.get("creator_handle") or ex.get("creator") or ex.get("author") or ""),
                    caption=str(ex.get("caption") or "")[:160],
                    plays=_to_int(ex.get("plays") or ex.get("play_count")) or 0,
                    likes=_to_int(ex.get("likes") or ex.get("like_count")) or 0,
                    published_at=str(ex.get("published_at") or ""),
                )
            )

        candidate = {
            "song_key": song_key,
            "title_key": make_title_only_key(title),
            "title": title,
            "artist": artist,
            "reels_rank": native_rank,
            "reels_count": _to_int(row.get("reel_count")),
            "reels_1d_growth": _to_int(row.get("growth_1d")),
            "reels_7d_growth": _to_int(row.get("growth_7d")),
            "reels_7d_growth_pct": round(growth_7d_pct, 1) if growth_7d_pct is not None else None,
            "reels_audio_url": str(row.get("audio_url") or ""),
            "reels_samples": [s.model_dump() for s in samples[:3]],
        }
        if song_key not in by_sound:
            by_sound[song_key] = candidate

    return list(by_sound.values())


def parse_shazam_charts_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize `automation-lab~shazam-charts-scraper` rows (`top-200` & `viral`)."""
    by_sound: Dict[str, Dict[str, Any]] = {}

    for row in items:
        if not isinstance(row, dict):
            continue
        raw_title = str(row.get("trackTitle") or row.get("title") or "").strip()
        artists_raw = row.get("artists") or []
        raw_artist = (
            str(artists_raw[0])
            if isinstance(artists_raw, list) and artists_raw
            else str(row.get("artist") or "")
        ).strip()
        rank = _to_int(row.get("rank"))
        if not raw_title or not raw_artist or rank is None:
            continue

        title = clean_track_title(raw_title)
        artist = clean_artist_name(raw_artist)
        if not title or not artist:
            continue

        song_key = make_song_key(title, artist)
        chart_type = str(row.get("chartType") or "top-200").lower()
        existing = by_sound.setdefault(
            song_key,
            {
                "song_key": song_key,
                "title_key": make_title_only_key(title),
                "title": title,
                "artist": artist,
                "shazam_global_rank": None,
                "shazam_viral_rank": None,
                "shazam_url": str(row.get("songUrl") or ""),
                "cover_url": str(row.get("artworkUrl") or ""),
            },
        )
        if chart_type == "viral":
            existing["shazam_viral_rank"] = rank
        else:
            existing["shazam_global_rank"] = rank
        if not existing.get("cover_url") and row.get("artworkUrl"):
            existing["cover_url"] = str(row["artworkUrl"])
        if not existing.get("shazam_url") and row.get("songUrl"):
            existing["shazam_url"] = str(row["songUrl"])

    return list(by_sound.values())


def parse_spotify_scraper_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize Spotify Viral 50 (`chart_viral_tracks` / playlists) & track play counts (`eduair94~spotify-scraper`)."""
    by_sound: Dict[str, Dict[str, Any]] = {}

    def _add_track(tr: Dict[str, Any], viral_pos: Optional[int] = None) -> None:
        raw_title = str(tr.get("name") or tr.get("title") or "").strip()
        artists_val = tr.get("artists") or tr.get("artist") or ""
        if isinstance(artists_val, list):
            first = artists_val[0] if artists_val else ""
            raw_artist = str(first.get("name") if isinstance(first, dict) else first).strip()
        else:
            raw_artist = str(artists_val).strip()

        if not raw_title or not raw_artist:
            return

        title = clean_track_title(raw_title)
        artist = clean_artist_name(raw_artist)
        song_key = make_song_key(title, artist)

        dur_ms = _to_int(tr.get("duration") or tr.get("durationMs") or tr.get("duration_ms"))
        duration_sec = int(dur_ms / 1000) if dur_ms and dur_ms > 1000 else dur_ms

        existing = by_sound.setdefault(
            song_key,
            {
                "song_key": song_key,
                "title_key": make_title_only_key(title),
                "title": title,
                "artist": artist,
                "spotify_viral_rank": None,
                "spotify_total_plays": None,
                "release_date": "",
                "cover_url": "",
                "preview_url": "",
                "preview_source": "",
                "duration_sec": None,
                "spotify_url": "",
            },
        )
        if viral_pos is not None and viral_pos > 0:
            cur_rank = existing["spotify_viral_rank"]
            if cur_rank is None or viral_pos < cur_rank:
                existing["spotify_viral_rank"] = viral_pos
        plays = _to_int(tr.get("playCount") or tr.get("playcount"))
        if plays and (not existing["spotify_total_plays"] or plays > existing["spotify_total_plays"]):
            existing["spotify_total_plays"] = plays
        if tr.get("releaseDate") and not existing["release_date"]:
            existing["release_date"] = str(tr["releaseDate"])[:10]
        cover = tr.get("albumArt") or tr.get("imageUrl") or tr.get("coverUrl") or ""
        if cover and not existing["cover_url"]:
            existing["cover_url"] = str(cover)
        preview = tr.get("audioPreviewUrl") or tr.get("previewUrl") or tr.get("preview_url") or ""
        if preview and not existing["preview_url"]:
            existing["preview_url"] = str(preview)
            existing["preview_source"] = "spotify"
        if duration_sec and not existing["duration_sec"]:
            existing["duration_sec"] = duration_sec
        sp_url = tr.get("url") or tr.get("trackUrl") or ""
        if sp_url and not existing["spotify_url"]:
            existing["spotify_url"] = str(sp_url)

    for row in items:
        if not isinstance(row, dict) or row.get("ok") is False:
            continue
        if isinstance(row.get("tracks"), list) and row["tracks"]:
            # Playlist response (legacy / editorial playlist fallback)
            for idx, tr in enumerate(row["tracks"], start=1):
                if isinstance(tr, dict):
                    _add_track(tr, viral_pos=idx)
        elif row.get("category") == "chart_viral_tracks" or row.get("mode") == "chart":
            viral_pos = _to_int(row.get("rank") or row.get("position"))
            _add_track(row, viral_pos=viral_pos)
        else:
            _add_track(row, viral_pos=None)

    return list(by_sound.values())


# ---------------------------------------------------------------------------
# Async Apify REST v2 Client
# ---------------------------------------------------------------------------


class ApifyCollectorClient:
    """Async Apify REST client running 5 complementary music/social actors inside weekly budget caps."""

    def __init__(self, token: Optional[str] = None) -> None:
        self.token = (token if token is not None else os.environ.get("APIFY_API_TOKEN", "")).strip()

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "User-Agent": "TrendPulse/3.0",
        }

    async def get_account_status(self) -> Dict[str, Any]:
        """Return live Apify username, plan, monthly limit, used USD, and remaining USD ($0.00 call)."""
        if not self.token:
            return {
                "configured": False,
                "connected": False,
                "error": "No hay APIFY_API_TOKEN configurado.",
            }

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                me_resp, lim_resp = await asyncio.gather(
                    client.get(f"{APIFY_BASE_URL}/users/me", headers=self._headers()),
                    client.get(f"{APIFY_BASE_URL}/users/me/limits", headers=self._headers()),
                )

            if me_resp.status_code == 401:
                return {
                    "configured": True,
                    "connected": False,
                    "auth_error": True,
                    "error": "Token de Apify inválido o revocado (HTTP 401).",
                }
            me_resp.raise_for_status()
            me_data = me_resp.json().get("data", {})

            monthly_limit = 5.0
            monthly_used = 0.0
            if lim_resp.status_code == 200:
                lim_data = lim_resp.json().get("data", {})
                monthly_limit = float((lim_data.get("limits") or {}).get("maxMonthlyUsageUsd") or 5.0)
                monthly_used = float((lim_data.get("current") or {}).get("monthlyUsageUsd") or 0.0)

            plan_obj = me_data.get("plan") or {}
            return {
                "configured": True,
                "connected": True,
                "auth_error": False,
                "username": str(me_data.get("username") or me_data.get("email") or ""),
                "plan": str(plan_obj.get("id") or plan_obj.get("description") or "FREE"),
                "monthly_limit_usd": round(monthly_limit, 4),
                "monthly_used_usd": round(monthly_used, 4),
                "remaining_usd": max(0.0, round(monthly_limit - monthly_used, 4)),
            }
        except httpx.HTTPError as exc:
            return {
                "configured": True,
                "connected": False,
                "auth_error": False,
                "error": f"No se pudo conectar con Apify ({type(exc).__name__}).",
            }

    async def _run_actor(
        self,
        actor_id: str,
        payload: Dict[str, Any],
        max_charge_usd: float,
        wait_seconds: int = 120,
    ) -> Tuple[str, float, List[Dict[str, Any]]]:
        """Run an Apify actor capped by `maxTotalChargeUsd` and return `(run_id, cost_usd, items)`."""
        if not self.token:
            raise ValueError("APIFY_API_TOKEN no está configurado.")

        cap = max(0.04, min(float(max_charge_usd), 2.5))
        encoded_actor = quote(actor_id, safe="~")
        url = (
            f"{APIFY_BASE_URL}/acts/{encoded_actor}/runs"
            f"?waitForFinish={wait_seconds}&maxTotalChargeUsd={cap:.2f}"
        )

        async with httpx.AsyncClient(timeout=httpx.Timeout(160.0, connect=15.0)) as client:
            try:
                resp = await client.post(url, headers=self._headers(), json=payload)
            except httpx.TimeoutException as exc:
                raise RuntimeError(f"Tiempo de espera agotado al iniciar {actor_id}") from exc
            if resp.status_code == 401:
                raise RuntimeError("Token Apify inválido o revocado (HTTP 401).")
            if resp.status_code == 402:
                raise RuntimeError("Saldo o límite mensual Apify agotado (HTTP 402).")
            if resp.status_code in (403, 429):
                raise RuntimeError(f"Apify rechazó la solicitud HTTP {resp.status_code}: {resp.text[:140]}")
            resp.raise_for_status()
            run_data = resp.json().get("data", {})

            run_id = str(run_data.get("id") or "")
            status = str(run_data.get("status") or "")
            dataset_id = str(run_data.get("defaultDatasetId") or "")

            polls = 0
            while status in ("READY", "RUNNING") and polls < 30:
                await asyncio.sleep(5)
                polls += 1
                p_resp = await client.get(f"{APIFY_BASE_URL}/actor-runs/{run_id}", headers=self._headers())
                p_resp.raise_for_status()
                run_data = p_resp.json().get("data", {})
                status = str(run_data.get("status") or "")
                dataset_id = str(run_data.get("defaultDatasetId") or dataset_id)

            cost_usd = float(run_data.get("usageTotalUsd") or 0.0)
            if status not in ("SUCCEEDED", "TIMED-OUT") and not dataset_id:
                raise RuntimeError(f"Actor {actor_id} terminó en estado '{status}'")

            items: List[Dict[str, Any]] = []
            if dataset_id:
                ds_resp = await client.get(
                    f"{APIFY_BASE_URL}/datasets/{dataset_id}/items?format=json&clean=true&limit=350",
                    headers=self._headers(),
                )
                if ds_resp.status_code == 200 and isinstance(ds_resp.json(), list):
                    items = ds_resp.json()

            return run_id, round(cost_usd, 4), items

    async def fetch_all_apify_trends(
        self,
        max_budget_usd: float = 1.05,
        spotify_track_urls: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Run up to 5 Apify actors concurrently inside `max_budget_usd` and remaining monthly credit."""
        empty_result: Dict[str, Any] = {
            "history_songs": [],
            "explore_songs": [],
            "reels_songs": [],
            "shazam_songs": [],
            "spotify_extra_songs": [],
            "statuses": [],
            "total_cost_usd": 0.0,
        }

        actor_meta = (
            ("tiktok_growth_history", "TikTok 7D Crecimiento Multi-País (Apify)"),
            ("tiktok_explore_sounds", "TikTok Explore 4 Mercados US/GB/MX/ES (Apify)"),
            ("instagram_reels_audio", "Instagram Reels Audio 7D (Apify)"),
            ("shazam_global_charts", "Shazam Top 200 & Viral 50 Global (Apify)"),
            ("spotify_viral_plays", "Spotify Viral 50 + Reproducciones Totales (Apify)"),
        )

        if not self.token:
            msg = "Fuente de pago no activa en esta ejecución; se conservaron únicamente las fuentes gratuitas."
            empty_result["statuses"] = [
                SourceStatus(id=sid, name=label, kind="apify", status="skipped", note=msg)
                for sid, label in actor_meta
            ]
            return empty_result

        account = await self.get_account_status()
        if account.get("auth_error"):
            msg = "Error de autenticación con el proveedor de pago (HTTP 401). Se conservó solo la actualización gratuita."
            empty_result["statuses"] = [
                SourceStatus(id=sid, name=label, kind="apify", status="error", note=msg)
                for sid, label in actor_meta
            ]
            return empty_result

        remaining = float(account.get("remaining_usd") or 0.0) if account.get("connected") else max_budget_usd
        effective_budget = round(min(max_budget_usd, max(0.0, remaining)), 4)

        if effective_budget < 0.08:
            msg = (
                "Cuota de fuentes de pago insuficiente para ejecutar extracción; "
                "actualización completada solo con fuentes gratuitas."
            )
            empty_result["statuses"] = [
                SourceStatus(id=sid, name=label, kind="apify", status="skipped", note=msg)
                for sid, label in actor_meta
            ]
            return empty_result

        # Allocate proportional per-actor caps summing <= effective_budget (~$0.92 nominal at $1.05 cap)
        scale = min(1.0, effective_budget / 1.05)

        async def _run_tiktok_history() -> Tuple[str, SourceStatus, List[Dict[str, Any]]]:
            cap = round(max(0.08, 0.34 * scale), 2)
            base_payload = {
                "mode": "insights",
                "countries": ["US", "MX", "BR", "DE"],
                "chartTypes": ["viral", "popular"],
                "lookbackDays": 7,
                "sortBy": "usage_change",
                "growthFilter": "rising",
                "includeExamples": True,
                "maxRows": 100,
            }
            cost = 0.0
            try:
                _, c1, raw = await self._run_actor(ACTOR_TIKTOK_HISTORY, base_payload, max_charge_usd=cap)
                cost += c1
                parsed = parse_history_insights_items(raw)
                if not parsed:
                    _, c2, raw2 = await self._run_actor(
                        ACTOR_TIKTOK_HISTORY,
                        {**base_payload, "countries": ["US", "MX"]},
                        max_charge_usd=max(0.06, cap - cost),
                    )
                    cost += c2
                    parsed = parse_history_insights_items(raw2)
                if not parsed:
                    _, c3, raw3 = await self._run_actor(
                        ACTOR_TIKTOK_HISTORY,
                        {**base_payload, "countries": ["US"], "maxRows": 60},
                        max_charge_usd=max(0.06, cap - cost),
                    )
                    cost += c3
                    parsed = parse_history_insights_items(raw3)
                return (
                    "history_songs",
                    SourceStatus(
                        id="tiktok_growth_history",
                        name="TikTok 7D Crecimiento Multi-País (Apify)",
                        kind="apify",
                        status="ok" if parsed else "error",
                        items_collected=len(parsed),
                        cost_usd=round(cost, 4),
                        note="" if parsed else "Sin filas de crecimiento en dataset.",
                    ),
                    parsed,
                )
            except Exception as exc:
                return (
                    "history_songs",
                    SourceStatus(
                        id="tiktok_growth_history",
                        name="TikTok 7D Crecimiento Multi-País (Apify)",
                        kind="apify",
                        status="error",
                        cost_usd=round(cost, 4),
                        note=str(exc)[:140],
                    ),
                    [],
                )

        async def _run_tiktok_explore() -> Tuple[str, SourceStatus, List[Dict[str, Any]]]:
            cap = round(max(0.08, 0.30 * scale), 2)
            try:
                _, cost, raw = await self._run_actor(
                    ACTOR_TIKTOK_EXPLORE,
                    {
                        "countries": ["US", "GB", "MX", "ES"],
                        "categories": ["All"],
                        "sampleVideos": 800 if scale >= 0.7 else 400,
                        "maxSounds": 60,
                        "minVideos": 2,
                        "excludeOriginalSounds": True,
                        "downloadAudio": False,
                        "onlyNew": False,
                    },
                    max_charge_usd=cap,
                )
                parsed = parse_explore_sounds_items(raw)
                return (
                    "explore_songs",
                    SourceStatus(
                        id="tiktok_explore_sounds",
                        name="TikTok Explore 4 Mercados US/GB/MX/ES (Apify)",
                        kind="apify",
                        status="ok" if parsed else "error",
                        items_collected=len(parsed),
                        cost_usd=round(cost, 4),
                        note="" if parsed else "Sin canciones encontradas en Explore.",
                    ),
                    parsed,
                )
            except Exception as exc:
                return (
                    "explore_songs",
                    SourceStatus(
                        id="tiktok_explore_sounds",
                        name="TikTok Explore 4 Mercados US/GB/MX/ES (Apify)",
                        kind="apify",
                        status="error",
                        note=str(exc)[:140],
                    ),
                    [],
                )

        async def _run_instagram_reels() -> Tuple[str, SourceStatus, List[Dict[str, Any]]]:
            cap = round(max(0.06, 0.21 * scale), 2)
            try:
                _, cost, raw = await self._run_actor(
                    ACTOR_IG_REELS,
                    {
                        "mode": "latest",
                        "kind": "catalogue",
                        "sortBy": "growth7d",
                        "maxRows": 60,
                        "includeExamples": True,
                    },
                    max_charge_usd=cap,
                )
                parsed = parse_instagram_reels_items(raw)
                return (
                    "reels_songs",
                    SourceStatus(
                        id="instagram_reels_audio",
                        name="Instagram Reels Audio 7D (Apify)",
                        kind="apify",
                        status="ok" if parsed else "error",
                        items_collected=len(parsed),
                        cost_usd=round(cost, 4),
                        note="" if parsed else "Sin filas de Reels en dataset.",
                    ),
                    parsed,
                )
            except Exception as exc:
                return (
                    "reels_songs",
                    SourceStatus(
                        id="instagram_reels_audio",
                        name="Instagram Reels Audio 7D (Apify)",
                        kind="apify",
                        status="error",
                        note=str(exc)[:140],
                    ),
                    [],
                )

        async def _run_shazam_charts() -> Tuple[str, SourceStatus, List[Dict[str, Any]]]:
            cap = round(max(0.05, 0.11 * scale), 2)
            try:
                _, cost, raw = await self._run_actor(
                    ACTOR_SHAZAM_CHARTS,
                    {
                        "startUrls": [
                            {"url": "https://www.shazam.com/charts/top-200/world"},
                            {"url": "https://www.shazam.com/charts/viral/world"},
                        ],
                        "maxItems": 250,
                        "maxItemsPerChart": 200,
                        "proxyConfiguration": {"useApifyProxy": True},
                    },
                    max_charge_usd=cap,
                )
                parsed = parse_shazam_charts_items(raw)
                return (
                    "shazam_songs",
                    SourceStatus(
                        id="shazam_global_charts",
                        name="Shazam Top 200 & Viral 50 Global (Apify)",
                        kind="apify",
                        status="ok" if parsed else "error",
                        items_collected=len(parsed),
                        cost_usd=round(cost, 4),
                        note="" if parsed else "Sin resultados en Shazam Global.",
                    ),
                    parsed,
                )
            except Exception as exc:
                return (
                    "shazam_songs",
                    SourceStatus(
                        id="shazam_global_charts",
                        name="Shazam Top 200 & Viral 50 Global (Apify)",
                        kind="apify",
                        status="error",
                        note=str(exc)[:140],
                    ),
                    [],
                )

        async def _run_spotify_scraper() -> Tuple[str, SourceStatus, List[Dict[str, Any]]]:
            viral_cap = round(max(0.05, 0.07 * scale), 2)
            tracks_cap = round(max(0.03, 0.04 * scale), 2)
            clean_tracks = [u for u in (spotify_track_urls or []) if "/track/" in u][:24]

            async def _fetch_viral() -> Tuple[float, List[Dict[str, Any]]]:
                _, cost_v, items_v = await self._run_actor(
                    ACTOR_SPOTIFY_SCRAPER,
                    {
                        "category": "chart_viral_tracks",
                        "queries": [SPOTIFY_VIRAL_CHART_QUERY],
                        "maxResultsPerQuery": 50,
                        "include": ["playcounts"],
                    },
                    max_charge_usd=viral_cap,
                )
                return cost_v, items_v

            async def _fetch_tracks() -> Tuple[float, List[Dict[str, Any]]]:
                if not clean_tracks:
                    return 0.0, []
                _, cost_t, items_t = await self._run_actor(
                    ACTOR_SPOTIFY_SCRAPER,
                    {
                        "category": "auto",
                        "queries": clean_tracks,
                    },
                    max_charge_usd=tracks_cap,
                )
                return cost_t, items_t

            res_viral, res_tracks = await asyncio.gather(
                _fetch_viral(),
                _fetch_tracks(),
                return_exceptions=True,
            )

            total_sp_cost = 0.0
            raw_items: List[Dict[str, Any]] = []
            notes: List[str] = []

            if isinstance(res_viral, Exception):
                notes.append(f"Viral 50: {str(res_viral)[:80]}")
            else:
                total_sp_cost += res_viral[0]
                raw_items.extend(res_viral[1])

            if isinstance(res_tracks, Exception):
                notes.append(f"Plays: {str(res_tracks)[:80]}")
            else:
                total_sp_cost += res_tracks[0]
                raw_items.extend(res_tracks[1])

            parsed = parse_spotify_scraper_items(raw_items)
            viral_count = sum(1 for item in parsed if item.get("spotify_viral_rank") is not None)
            if parsed and viral_count == 0 and not notes:
                notes.append("Spotify Viral 50 sin filas.")
            if not parsed and not notes:
                notes.append("Sin tracks en respuesta Spotify.")

            return (
                "spotify_extra_songs",
                SourceStatus(
                    id="spotify_viral_plays",
                    name="Spotify Viral 50 + Reproducciones Totales (Apify)",
                    kind="apify",
                    status="ok" if (parsed and viral_count > 0) else "error",
                    items_collected=len(parsed),
                    cost_usd=round(total_sp_cost, 4),
                    note="; ".join(notes),
                ),
                parsed,
            )

        actor_specs = [
            ("history_songs", "tiktok_growth_history", "TikTok 7D Crecimiento Multi-País (Apify)", 0.12, _run_tiktok_history),
            ("shazam_songs", "shazam_global_charts", "Shazam Top 200 & Viral 50 Global (Apify)", 0.08, _run_shazam_charts),
            ("spotify_extra_songs", "spotify_viral_plays", "Spotify Viral 50 + Reproducciones Totales (Apify)", 0.06, _run_spotify_scraper),
            ("reels_songs", "instagram_reels_audio", "Instagram Reels Audio 7D (Apify)", 0.12, _run_instagram_reels),
            ("explore_songs", "tiktok_explore_sounds", "TikTok Explore 4 Mercados US/GB/MX/ES (Apify)", 0.12, _run_tiktok_explore),
        ]

        out = dict(empty_result)
        statuses_by_id: Dict[str, SourceStatus] = {}
        total_cost = 0.0

        if effective_budget >= 0.85:
            # Plenty of budget: run all 5 Apify actors concurrently; isolated per-actor failures never crash the run
            outcomes = await asyncio.gather(*[fn() for _, _, _, _, fn in actor_specs])
            for result_key, st, data_list in outcomes:
                out[result_key] = data_list
                statuses_by_id[st.id] = st
                total_cost += st.cost_usd
        else:
            # Low budget / remaining balance mode: run highest-priority sources sequentially as far as credit allows
            budget_left = effective_budget
            quota_exhausted = False
            for result_key, sid, label, min_needed, fn in actor_specs:
                if quota_exhausted or budget_left < min_needed:
                    reason = (
                        "Cuota del proveedor de pago agotada durante la corrida; se conservaron las fuentes previas."
                        if quota_exhausted
                        else "Cuota restante del proveedor de pago insuficiente para esta fuente; se conservaron las anteriores y las gratuitas."
                    )
                    statuses_by_id[sid] = SourceStatus(
                        id=sid,
                        name=label,
                        kind="apify",
                        status="skipped",
                        note=reason,
                    )
                    continue
                r_key, st, data_list = await fn()
                out[r_key] = data_list
                statuses_by_id[st.id] = st
                total_cost += st.cost_usd
                budget_left = max(0.0, budget_left - st.cost_usd)
                if st.status == "error" and ("402" in st.note or "agotado" in st.note.lower() or "401" in st.note):
                    quota_exhausted = True

        out["statuses"] = [statuses_by_id[sid] for _, sid, _, _, _ in actor_specs if sid in statuses_by_id]
        out["total_cost_usd"] = round(total_cost, 4)
        return out
