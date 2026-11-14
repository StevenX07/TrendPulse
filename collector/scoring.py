"""Cross-source deduplication, 7-day volume scoring, rapid-growth velocity, and week-over-week diffs."""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .models import WeeklySnapshot, WeeklySongTrend
from .normalization import make_song_key, make_title_only_key, strip_accents


def _artist_tokens(artist: str) -> set[str]:
    clean = strip_accents(artist or "").lower()
    tokens = {t for t in re.findall(r"[a-z0-9]+", clean) if len(t) >= 2}
    tokens.discard("trending")
    tokens.discard("youtube")
    tokens.discard("tiktok")
    tokens.discard("artist")
    return tokens


def _parse_rank_jump(raw: Optional[str]) -> Tuple[int, bool]:
    """Return `(positive_jump_places, is_new_entry)` from strings like `+14`, `NEW`, `-3`, `=`."""
    val = (raw or "").strip().upper()
    if not val or val == "=":
        return 0, False
    if "NEW" in val or "RE" == val:
        return 0, True
    m = re.search(r"([+-]?\d+)", val)
    if not m:
        return 0, False
    try:
        num = int(m.group(1))
        return max(0, num), False
    except ValueError:
        return 0, False


def _resolve_target_key(
    records: Dict[str, Dict[str, Any]],
    title_index: Dict[str, List[str]],
    raw_item: Dict[str, Any],
) -> str:
    """Match an incoming track to an existing merged song key when collaborating/formatted slightly differently."""
    title = str(raw_item.get("title") or "").strip()
    artist = str(raw_item.get("artist") or "").strip()
    canonical = str(raw_item.get("song_key") or make_song_key(title, artist))
    if canonical in records:
        return canonical

    t_key = str(raw_item.get("title_key") or make_title_only_key(title))
    if not t_key:
        return canonical

    incoming_tokens = _artist_tokens(artist)
    for existing_key in title_index.get(t_key, []):
        existing = records[existing_key]
        existing_tokens = _artist_tokens(existing.get("artist", ""))
        if not incoming_tokens or not existing_tokens:
            return existing_key
        if incoming_tokens & existing_tokens:
            return existing_key

    return canonical


def _ensure_record(
    records: Dict[str, Dict[str, Any]],
    title_index: Dict[str, List[str]],
    raw_item: Dict[str, Any],
    updated_at: str,
) -> Dict[str, Any]:
    key = _resolve_target_key(records, title_index, raw_item)
    if key not in records:
        title = str(raw_item.get("title") or "").strip()
        artist = str(raw_item.get("artist") or "").strip() or "Artista"
        t_key = str(raw_item.get("title_key") or make_title_only_key(title))
        records[key] = {
            "song_key": key,
            "title": title,
            "artist": artist,
            "cover_url": "",
            "preview_url": "",
            "preview_source": "",
            "duration_sec": None,
            "bpm": None,
            "release_date": "",
            "genres": [],
            "spotify_url": "",
            "youtube_video_id": "",
            "youtube_url": "",
            "tiktok_sound_id": "",
            "tiktok_sound_url": "",
            "tiktok_countries": [],
            "tiktok_samples": [],
            "reels_audio_url": "",
            "reels_samples": [],
            "shazam_url": "",
            "apple_music_url": "",
            "deezer_url": "",
            "platforms": [],
            "updated_at": updated_at,
        }
        if t_key:
            title_index.setdefault(t_key, []).append(key)

    rec = records[key]
    if rec.get("artist") in ("YouTube Trending", "YouTube Artist", "TikTok Trending", "Artista") and raw_item.get("artist"):
        cand_art = str(raw_item["artist"]).strip()
        if cand_art not in ("YouTube Trending", "YouTube Artist", "TikTok Trending"):
            rec["artist"] = cand_art
    return rec


def _add_platform(rec: Dict[str, Any], platform_name: str) -> None:
    if platform_name not in rec["platforms"]:
        rec["platforms"].append(platform_name)


def compute_trend_score(song: Dict[str, Any]) -> float:
    """Compute 0..100 score emphasizing 7-day global streaming volume & cross-platform reach."""
    score = 0.0

    # 1. Spotify 7D Streams & Viral 50 (max ~39 pts)
    sp_streams = song.get("spotify_weekly_streams") or 0
    sp_rank = song.get("spotify_rank")
    if sp_streams > 0:
        # 1M streams -> ~8 pts, 35M streams -> ~28 pts
        score += min(28.0, max(0.0, (math.log10(max(sp_streams, 100_000)) - 5.6) * 14.0))
    if sp_rank:
        score += max(0.0, (201 - sp_rank) / 200.0 * 9.0)
    sp_viral = song.get("spotify_viral_rank")
    if sp_viral:
        score += max(1.0, (51 - min(50, sp_viral)) / 50.0 * 5.0)
    sp_top50 = song.get("spotify_top50_rank")
    if sp_top50:
        score += max(1.0, (51 - min(50, sp_top50)) / 50.0 * 3.0)

    # 2. YouTube 7D Views (max ~24 pts)
    yt_views = song.get("youtube_weekly_views") or 0
    yt_rank = song.get("youtube_rank")
    if yt_views > 0:
        score += min(17.0, max(0.0, (math.log10(max(yt_views, 100_000)) - 5.8) * 8.5))
    if yt_rank:
        score += max(0.0, (201 - yt_rank) / 200.0 * 7.0)

    # 3. Apple Music, Billboard, Deezer, Shazam Global/Viral & Radio
    ap_rank = song.get("apple_rank")
    if ap_rank:
        score += max(0.0, (201 - ap_rank) / 200.0 * 9.0)
    bb_rank = song.get("billboard_rank")
    if bb_rank:
        score += max(0.0, (101 - bb_rank) / 100.0 * 8.0)
    if song.get("deezer_rank"):
        score += 4.5
    sh_global = song.get("shazam_global_rank") or song.get("shazam_rank")
    if sh_global:
        score += max(1.0, (201 - min(200, sh_global)) / 200.0 * 6.0)
    sh_viral = song.get("shazam_viral_rank")
    if sh_viral:
        score += max(1.5, (51 - min(50, sh_viral)) / 50.0 * 4.5)

    # 4. TikTok & Instagram Reels Social Signals
    tt_rank = song.get("tiktok_rank")
    tt_plays = song.get("tiktok_explore_plays") or 0
    if tt_rank:
        score += max(2.0, (101 - min(100, tt_rank)) / 100.0 * 7.5)
    if tt_plays > 0:
        score += min(5.0, max(0.0, (math.log10(tt_plays) - 5.0) * 2.2))
    reels_rank = song.get("reels_rank")
    if reels_rank:
        score += max(1.5, (61 - min(60, reels_rank)) / 60.0 * 5.0)

    # 5. Cross-platform breadth bonus (max +12 pts)
    p_count = len(song.get("platforms") or [])
    if p_count > 1:
        score += min(12.0, (p_count - 1) * 2.8)

    return round(min(99.9, max(1.0, score)), 1)


def compute_velocity_score(song: Dict[str, Any]) -> Tuple[float, bool, str]:
    """Compute 0..100 rapid-growth acceleration score, `is_new_entry`, and best human badge."""
    score = 0.0
    badges: List[Tuple[float, str]] = []
    is_new = False

    # 1. Spotify 7D % growth & net delta
    sp_pct = song.get("spotify_weekly_growth_pct")
    sp_delta = song.get("spotify_weekly_delta") or 0
    sp_jump, sp_new = _parse_rank_jump(song.get("spotify_rank_change"))
    if sp_new:
        is_new = True
        score += 18.0
        badges.append((18.0, f"NEW #{song.get('spotify_rank')} Spotify"))
    if sp_pct and sp_pct > 0:
        pts = min(28.0, math.sqrt(sp_pct) * 3.4)
        score += pts
        badges.append((pts, f"+{sp_pct:.0f}% Spotify 7D"))
    if sp_delta > 0:
        pts = min(10.0, sp_delta / 600_000.0)
        score += pts
    if sp_jump > 0:
        pts = min(14.0, sp_jump * 0.45)
        score += pts
        if sp_jump >= 8:
            badges.append((pts + 4.0, f"↑{sp_jump} Spotify"))

    # 2. YouTube 7D growth & debuts
    yt_pct = song.get("youtube_weekly_growth_pct")
    yt_jump, yt_new = _parse_rank_jump(song.get("youtube_rank_change"))
    if yt_new:
        is_new = True
        score += 16.0
        badges.append((16.5, f"NEW #{song.get('youtube_rank')} YouTube"))
    if yt_pct and yt_pct > 0:
        pts = min(20.0, math.sqrt(yt_pct) * 2.6)
        score += pts
        badges.append((pts, f"+{yt_pct:.0f}% YouTube 7D"))
    if yt_jump >= 5:
        pts = min(12.0, yt_jump * 0.4)
        score += pts
        badges.append((pts, f"↑{yt_jump} YouTube"))

    # 3. TikTok 7D growth & Explore virality
    tt_pct = song.get("tiktok_7d_growth_pct")
    tt_chg = song.get("tiktok_7d_usage_change") or 0
    tt_is_new = bool(song.get("tiktok_is_new"))
    if tt_is_new:
        is_new = True
        score += 18.0
        badges.append((18.5, "NEW en TikTok"))
    if tt_pct and tt_pct > 0:
        pts = min(30.0, math.sqrt(tt_pct) * 2.8)
        score += pts
        badges.append((pts + 3.0, f"+{tt_pct:.0f}% TikTok 7D"))
    elif tt_chg > 0:
        pts = min(20.0, math.log10(max(tt_chg, 10)) * 3.8)
        score += pts
        badges.append((pts + 2.0, f"+{tt_chg:,} usos TikTok"))
    elif song.get("tiktok_explore_videos"):
        vids = song["tiktok_explore_videos"]
        pts = min(16.0, vids * 3.2)
        score += pts
        badges.append((pts, f"{vids} videos virales TikTok"))

    tt_countries = song.get("tiktok_countries") or []
    if len(tt_countries) >= 2:
        pts = min(8.0, (len(tt_countries) - 1) * 3.0)
        score += pts
        if len(tt_countries) >= 3:
            badges.append((pts + 3.0, f"TikTok {len(tt_countries)} países"))

    # 3b. Instagram Reels 7D growth
    reels_pct = song.get("reels_7d_growth_pct")
    reels_growth = song.get("reels_7d_growth") or 0
    reels_rank = song.get("reels_rank")
    if reels_pct and reels_pct > 0:
        pts = min(24.0, math.sqrt(reels_pct) * 2.5)
        score += pts
        badges.append((pts + 2.5, f"+{reels_pct:.0f}% Reels 7D"))
    elif reels_growth > 0:
        pts = min(15.0, math.log10(max(reels_growth, 10)) * 3.2)
        score += pts
        badges.append((pts + 1.5, f"+{reels_growth:,} Reels 7D"))
    if reels_rank and reels_rank <= 25:
        score += max(1.5, (26 - reels_rank) / 25.0 * 5.0)

    # 4. Spotify Viral 50, Shazam Viral/Global, Apple Music, Billboard, Radio deltas
    sp_viral = song.get("spotify_viral_rank")
    if sp_viral and sp_viral <= 50:
        pts = max(4.0, (51 - sp_viral) / 50.0 * 14.0)
        score += pts
        badges.append((pts + 2.0, f"Viral #{sp_viral} Spotify"))

    ap_jump, ap_new = _parse_rank_jump(song.get("apple_rank_change"))
    if ap_new:
        is_new = True
        score += 10.0
    elif ap_jump >= 5:
        pts = min(10.0, ap_jump * 0.35)
        score += pts
        badges.append((pts, f"↑{ap_jump} Apple"))

    bb_rank = song.get("billboard_rank")
    bb_last = song.get("billboard_last_week")
    if bb_rank and bb_last is None:
        is_new = True
        score += 14.0
        badges.append((14.0, f"NEW #{bb_rank} Billboard"))
    elif bb_rank and bb_last and bb_last > bb_rank:
        bb_jump = bb_last - bb_rank
        pts = min(14.0, bb_jump * 0.65)
        score += pts
        if bb_jump >= 5:
            badges.append((pts + 2.0, f"↑{bb_jump} Billboard"))

    sh_viral = song.get("shazam_viral_rank")
    if sh_viral and sh_viral <= 50:
        pts = max(5.0, (51 - sh_viral) / 50.0 * 13.0)
        score += pts
        badges.append((pts + 2.0, f"Shazam Viral #{sh_viral}"))

    shazam_rank = song.get("shazam_global_rank") or song.get("shazam_rank")
    if shazam_rank and shazam_rank <= 50:
        pts = max(3.0, (51 - shazam_rank) / 50.0 * 9.0)
        score += pts
        if shazam_rank <= 15:
            badges.append((pts, f"Shazam #{shazam_rank}"))

    rad_delta = song.get("radio_audience_delta")
    if rad_delta and rad_delta > 0.3:
        score += min(6.0, rad_delta * 2.0)

    # 5. Early breakout freshness bonus (charting <= 3 weeks or fresh release_date)
    sp_wks = song.get("spotify_weeks_on_chart")
    yt_wks = song.get("youtube_weeks_on_chart")
    bb_wks = song.get("billboard_weeks")
    min_wks = min([w for w in (sp_wks, yt_wks, bb_wks) if w is not None], default=None)
    if min_wks is not None and min_wks <= 3:
        score += (4 - min_wks) * 3.0
        if min_wks == 1:
            is_new = True

    rel_date = str(song.get("release_date") or "").strip()[:10]
    if len(rel_date) == 10:
        try:
            ref_dt = datetime.now(timezone.utc)
            if song.get("updated_at"):
                try:
                    ref_dt = datetime.fromisoformat(str(song["updated_at"]).replace("Z", "+00:00"))
                except ValueError:
                    pass
            rel_dt = datetime.strptime(rel_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            age_days = (ref_dt - rel_dt).days
            if 0 <= age_days <= 21:
                score += max(1.0, (22 - age_days) / 21.0 * 5.0)
                if age_days <= 10:
                    is_new = True
        except ValueError:
            pass

    badges.sort(key=lambda pair: pair[0], reverse=True)
    best_badge = badges[0][1] if badges else "Tendencia estable"
    return round(min(99.9, max(0.0, score)), 1), is_new, best_badge


def merge_all_sources(
    free_data: Dict[str, Any],
    apify_data: Dict[str, Any],
    updated_at: str,
) -> List[Dict[str, Any]]:
    """Merge all 9 free sources + up to 5 Apify actors into deduplicated scored dicts."""
    records: Dict[str, Dict[str, Any]] = {}
    title_index: Dict[str, List[str]] = {}

    # 1. Spotify Global Weekly (primary 7D stream truth)
    for row in free_data.get("spotify_weekly", []):
        rec = _ensure_record(records, title_index, row, updated_at)
        _add_platform(rec, "Spotify")
        rec["spotify_rank"] = row["rank"]
        rec["spotify_rank_change"] = row.get("rank_change")
        rec["spotify_weekly_streams"] = row.get("weekly_streams")
        rec["spotify_weekly_delta"] = row.get("weekly_delta")
        rec["spotify_weekly_growth_pct"] = row.get("weekly_growth_pct")
        rec["spotify_weeks_on_chart"] = row.get("weeks_on_chart")
        rec["spotify_peak_rank"] = row.get("peak_rank")
        if row.get("spotify_url"):
            rec["spotify_url"] = row["spotify_url"]

    # 2. Spotify Global Daily (adds daily_streams & fills new debuts not yet in weekly print)
    for row in free_data.get("spotify_daily", []):
        rec = _ensure_record(records, title_index, row, updated_at)
        _add_platform(rec, "Spotify")
        rec["spotify_daily_streams"] = row.get("daily_streams")
        if not rec.get("spotify_rank"):
            rec["spotify_rank"] = row["rank"]
            rec["spotify_rank_change"] = row.get("rank_change")
        if not rec.get("spotify_weekly_streams") and row.get("seven_day_streams"):
            rec["spotify_weekly_streams"] = row["seven_day_streams"]
            rec["spotify_weekly_delta"] = row.get("seven_day_delta")
            rec["spotify_weekly_growth_pct"] = row.get("seven_day_growth_pct")
        if not rec.get("spotify_url") and row.get("spotify_url"):
            rec["spotify_url"] = row["spotify_url"]

    # 3. YouTube Global Weekly
    for row in free_data.get("youtube_weekly", []):
        rec = _ensure_record(records, title_index, row, updated_at)
        _add_platform(rec, "YouTube")
        rec["youtube_rank"] = row["rank"]
        rec["youtube_rank_change"] = row.get("rank_change")
        rec["youtube_weekly_views"] = row.get("weekly_views")
        rec["youtube_weekly_delta"] = row.get("weekly_delta")
        rec["youtube_weekly_growth_pct"] = row.get("weekly_growth_pct")
        rec["youtube_weeks_on_chart"] = row.get("weeks_on_chart")
        if row.get("youtube_video_id"):
            rec["youtube_video_id"] = row["youtube_video_id"]
            rec["youtube_url"] = row.get("youtube_url") or f"https://www.youtube.com/watch?v={row['youtube_video_id']}"
            if not rec.get("cover_url"):
                rec["cover_url"] = f"https://i.ytimg.com/vi/{row['youtube_video_id']}/hqdefault.jpg"

    # 4. YouTube Music Global (ytmusicapi)
    for row in free_data.get("ytmusic_charts", []):
        rec = _ensure_record(records, title_index, row, updated_at)
        _add_platform(rec, "YouTube")
        if not rec.get("youtube_rank"):
            rec["youtube_rank"] = row["rank"]
        if not rec.get("youtube_video_id") and row.get("youtube_video_id"):
            rec["youtube_video_id"] = row["youtube_video_id"]
            rec["youtube_url"] = row.get("youtube_url", "")
        if not rec.get("cover_url") and row.get("cover_url"):
            rec["cover_url"] = row["cover_url"]

    # 5. Apple Music Worldwide
    for row in free_data.get("apple_music", []):
        rec = _ensure_record(records, title_index, row, updated_at)
        _add_platform(rec, "Apple Music")
        rec["apple_rank"] = row["rank"]
        rec["apple_rank_change"] = row.get("rank_change")
        rec["apple_points"] = row.get("points")
        rec["apple_points_delta"] = row.get("points_delta")

    # 6. iTunes RSS Top Songs (instant 30s AAC preview + genre + HD art)
    for row in free_data.get("itunes_rss", []):
        rec = _ensure_record(records, title_index, row, updated_at)
        _add_platform(rec, "Apple Music")
        if not rec.get("preview_url") and row.get("preview_url"):
            rec["preview_url"] = row["preview_url"]
            rec["preview_source"] = "itunes"
        if not rec.get("cover_url") and row.get("cover_url"):
            rec["cover_url"] = row["cover_url"]
        if not rec.get("apple_music_url") and row.get("apple_music_url"):
            rec["apple_music_url"] = row["apple_music_url"]
        if row.get("genre") and row["genre"] not in rec["genres"]:
            rec["genres"].append(row["genre"])

    # 7. Deezer Global Chart (30s MP3 fallback + HD art + rank + duration)
    for row in free_data.get("deezer_chart", []):
        rec = _ensure_record(records, title_index, row, updated_at)
        _add_platform(rec, "Deezer")
        rec["deezer_rank"] = row.get("deezer_rank") or row.get("rank")
        if not rec.get("preview_url") and row.get("preview_url"):
            rec["preview_url"] = row["preview_url"]
            rec["preview_source"] = "deezer"
        if not rec.get("cover_url") and row.get("cover_url"):
            rec["cover_url"] = row["cover_url"]
        if not rec.get("duration_sec") and row.get("duration_sec"):
            rec["duration_sec"] = row["duration_sec"]
        if row.get("deezer_url"):
            rec["deezer_url"] = row["deezer_url"]

    # 8. Billboard Hot 100 Weekly
    for row in free_data.get("billboard_hot100", []):
        rec = _ensure_record(records, title_index, row, updated_at)
        _add_platform(rec, "Billboard")
        rec["billboard_rank"] = row["rank"]
        rec["billboard_last_week"] = row.get("last_week")
        rec["billboard_peak"] = row.get("peak")
        rec["billboard_weeks"] = row.get("weeks")

    # 9. Kworb Radio & Shazam Cross-Rank
    for row in free_data.get("radio_shazam", []):
        rec = _ensure_record(records, title_index, row, updated_at)
        if row.get("shazam_rank"):
            _add_platform(rec, "Shazam")
            rec["shazam_rank"] = row["shazam_rank"]
        rec["radio_rank"] = row.get("radio_rank")
        rec["radio_audience_m"] = row.get("radio_audience_m")
        rec["radio_audience_delta"] = row.get("radio_audience_delta")

    # 10. Apify TikTok 7D Growth History (Multi-Country)
    for row in apify_data.get("history_songs", []):
        rec = _ensure_record(records, title_index, row, updated_at)
        _add_platform(rec, "TikTok")
        rec["tiktok_sound_id"] = row.get("tiktok_sound_id") or rec.get("tiktok_sound_id", "")
        rec["tiktok_rank"] = row.get("tiktok_rank") or rec.get("tiktok_rank")
        rec["tiktok_chart_type"] = row.get("tiktok_chart_type") or rec.get("tiktok_chart_type", "")
        for cc in row.get("tiktok_countries") or []:
            if cc not in rec["tiktok_countries"]:
                rec["tiktok_countries"].append(cc)
        rec["tiktok_usage_count"] = row.get("tiktok_usage_count")
        rec["tiktok_7d_usage_change"] = row.get("tiktok_7d_usage_change")
        rec["tiktok_7d_growth_pct"] = row.get("tiktok_7d_growth_pct")
        rec["tiktok_rank_change"] = row.get("tiktok_rank_change")
        rec["tiktok_is_viral"] = bool(row.get("tiktok_is_viral"))
        if row.get("tiktok_is_commercial") is not None:
            rec["tiktok_is_commercial"] = row["tiktok_is_commercial"]
        if row.get("tiktok_sound_url"):
            rec["tiktok_sound_url"] = row["tiktok_sound_url"]
        if row.get("cover_url") and not rec.get("cover_url"):
            rec["cover_url"] = row["cover_url"]
        for link_field in ("spotify_url", "apple_music_url", "youtube_url"):
            if not rec.get(link_field) and row.get(link_field):
                rec[link_field] = row[link_field]
        if row.get("tiktok_samples"):
            rec["tiktok_samples"] = row["tiktok_samples"]

    # 11. Apify TikTok Explore Sounds (4 Markets)
    for row in apify_data.get("explore_songs", []):
        rec = _ensure_record(records, title_index, row, updated_at)
        _add_platform(rec, "TikTok")
        if not rec.get("tiktok_sound_id") and row.get("tiktok_sound_id"):
            rec["tiktok_sound_id"] = row["tiktok_sound_id"]
        if row.get("tiktok_rank") and (not rec.get("tiktok_rank") or row["tiktok_rank"] < rec["tiktok_rank"]):
            rec["tiktok_rank"] = row["tiktok_rank"]
        if not rec.get("tiktok_chart_type"):
            rec["tiktok_chart_type"] = "explore"
        for cc in row.get("tiktok_countries") or []:
            if cc not in rec["tiktok_countries"]:
                rec["tiktok_countries"].append(cc)
        rec["tiktok_explore_videos"] = row.get("tiktok_explore_videos")
        rec["tiktok_explore_plays"] = row.get("tiktok_explore_plays")
        rec["tiktok_is_new"] = bool(row.get("tiktok_is_new"))
        rec["tiktok_is_viral"] = bool(rec.get("tiktok_is_viral") or row.get("tiktok_is_viral"))
        if rec.get("tiktok_is_commercial") is None and row.get("tiktok_is_commercial") is not None:
            rec["tiktok_is_commercial"] = row["tiktok_is_commercial"]
        rec["tiktok_newest_age_days"] = row.get("tiktok_newest_age_days")
        if not rec.get("tiktok_sound_url") and row.get("tiktok_sound_url"):
            rec["tiktok_sound_url"] = row["tiktok_sound_url"]
        if not rec.get("cover_url") and row.get("cover_url"):
            rec["cover_url"] = row["cover_url"]
        if not rec.get("preview_url") and row.get("preview_url"):
            rec["preview_url"] = row["preview_url"]
            rec["preview_source"] = "tiktok"
        if row.get("tiktok_samples") and not rec.get("tiktok_samples"):
            rec["tiktok_samples"] = row["tiktok_samples"]

    # 12. Apify Instagram Reels Audio 7D
    for row in apify_data.get("reels_songs", []):
        rec = _ensure_record(records, title_index, row, updated_at)
        _add_platform(rec, "Reels")
        rec["reels_rank"] = row.get("reels_rank") or rec.get("reels_rank")
        rec["reels_count"] = row.get("reels_count")
        rec["reels_1d_growth"] = row.get("reels_1d_growth")
        rec["reels_7d_growth"] = row.get("reels_7d_growth")
        rec["reels_7d_growth_pct"] = row.get("reels_7d_growth_pct")
        if row.get("reels_audio_url"):
            rec["reels_audio_url"] = row["reels_audio_url"]
        if row.get("reels_samples"):
            rec["reels_samples"] = row["reels_samples"]

    # 13. Apify Shazam Global Top 200 & Viral 50
    for row in apify_data.get("shazam_songs", []):
        rec = _ensure_record(records, title_index, row, updated_at)
        _add_platform(rec, "Shazam")
        if row.get("shazam_global_rank"):
            rec["shazam_global_rank"] = row["shazam_global_rank"]
            if not rec.get("shazam_rank") or row["shazam_global_rank"] < rec["shazam_rank"]:
                rec["shazam_rank"] = row["shazam_global_rank"]
        if row.get("shazam_viral_rank"):
            rec["shazam_viral_rank"] = row["shazam_viral_rank"]
            if not rec.get("shazam_rank"):
                rec["shazam_rank"] = row["shazam_viral_rank"]
        if row.get("shazam_url"):
            rec["shazam_url"] = row["shazam_url"]
        if row.get("cover_url") and not rec.get("cover_url"):
            rec["cover_url"] = row["cover_url"]

    # 14. Apify Spotify Top 50, Viral 50 Global + Cumulative Play Counts & Release Dates
    for row in apify_data.get("spotify_extra_songs", []):
        rec = _ensure_record(records, title_index, row, updated_at)
        _add_platform(rec, "Spotify")
        if row.get("spotify_top50_rank"):
            rec["spotify_top50_rank"] = row["spotify_top50_rank"]
        if row.get("spotify_viral_rank"):
            rec["spotify_viral_rank"] = row["spotify_viral_rank"]
        if row.get("spotify_total_plays"):
            rec["spotify_total_plays"] = row["spotify_total_plays"]
        if row.get("release_date") and not rec.get("release_date"):
            rec["release_date"] = row["release_date"]
        if row.get("duration_sec") and not rec.get("duration_sec"):
            rec["duration_sec"] = row["duration_sec"]
        if row.get("cover_url") and not rec.get("cover_url"):
            rec["cover_url"] = row["cover_url"]
        if row.get("spotify_url") and not rec.get("spotify_url"):
            rec["spotify_url"] = row["spotify_url"]
        if row.get("preview_url") and not rec.get("preview_url"):
            rec["preview_url"] = row["preview_url"]
            rec["preview_source"] = row.get("preview_source") or "spotify"

    # Final score pass
    out = list(records.values())
    for item in out:
        item["platform_count"] = len(item["platforms"])
        item["trend_score"] = compute_trend_score(item)
        vel, is_new, badge = compute_velocity_score(item)
        item["velocity_score"] = vel
        item["is_new_entry"] = is_new
        item["growth_badge"] = badge

    out.sort(key=lambda s: (s["trend_score"], s.get("spotify_weekly_streams") or 0), reverse=True)
    return out


def assign_ranks_and_wow(
    songs: List[WeeklySongTrend],
    previous_snapshot: Optional[WeeklySnapshot] = None,
) -> List[WeeklySongTrend]:
    """Assign overall & growth rankings and compare against the prior weekly snapshot."""
    prev_map: Dict[str, WeeklySongTrend] = (
        {s.song_key: s for s in previous_snapshot.songs}
        if previous_snapshot
        else {}
    )

    by_growth = sorted(songs, key=lambda s: (s.velocity_score, s.trend_score), reverse=True)
    growth_rank_map = {s.song_key: idx for idx, s in enumerate(by_growth, start=1)}

    songs_sorted = sorted(
        songs,
        key=lambda s: (s.trend_score, s.spotify_weekly_streams or 0, s.youtube_weekly_views or 0),
        reverse=True,
    )

    for idx, song in enumerate(songs_sorted, start=1):
        song.rank_overall = idx
        song.rank_growth = growth_rank_map.get(song.song_key, idx)
        prev = prev_map.get(song.song_key)
        if prev and prev.rank_overall:
            song.wow_rank_delta = prev.rank_overall - idx
            song.wow_score_delta = round(song.trend_score - prev.trend_score, 1)

    return songs_sorted
