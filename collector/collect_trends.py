"""CLI & programmatic weekly trend collector producing static JSON snapshots."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from dotenv import load_dotenv

from .models import (
    HistoryIndex,
    HistoryWeekEntry,
    SnapshotSummary,
    SourceStatus,
    WeeklySnapshot,
    WeeklySongTrend,
)
from .scoring import assign_ranks_and_wow, merge_all_sources
from .sources_apify import ApifyCollectorClient
from .sources_free import enrich_songs_metadata, fetch_all_free_sources

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PUBLIC_DATA_DIR = ROOT_DIR / "frontend" / "public" / "data"
DEFAULT_CACHE_PATH = ROOT_DIR / "data" / "track_meta_cache.json"


def _load_previous_snapshot(archive_dir: Path, current_week_id: str) -> Optional[WeeklySnapshot]:
    if not archive_dir.exists():
        return None
    files = sorted(archive_dir.glob("*.json"), reverse=True)
    for fpath in files:
        if fpath.stem == current_week_id:
            continue
        try:
            return WeeklySnapshot.model_validate_json(fpath.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.debug("Skipping unreadable archive %s: %s", fpath.name, exc)
    return None


def _rebuild_history_index(archive_dir: Path, updated_at: str) -> HistoryIndex:
    entries: List[HistoryWeekEntry] = []
    if archive_dir.exists():
        for fpath in sorted(archive_dir.glob("*.json"), reverse=True):
            try:
                snap = WeeklySnapshot.model_validate_json(fpath.read_text(encoding="utf-8"))
                song_map = {s.song_key: s for s in snap.songs}
                top_s = song_map.get(snap.summary.top_streamed_key) or (snap.songs[0] if snap.songs else None)
                fast_s = song_map.get(snap.summary.fastest_growth_key)
                entries.append(
                    HistoryWeekEntry(
                        week_id=snap.week_id,
                        generated_at=snap.generated_at,
                        mode=snap.mode,
                        total_songs=snap.summary.total_songs,
                        tiktok_songs_count=snap.summary.tiktok_songs_count,
                        reels_songs_count=snap.summary.reels_songs_count,
                        total_cost_usd=snap.summary.total_cost_usd,
                        top_streamed_title=top_s.title if top_s else "",
                        top_streamed_artist=top_s.artist if top_s else "",
                        fastest_growth_title=fast_s.title if fast_s else "",
                        fastest_growth_artist=fast_s.artist if fast_s else "",
                        archive_path=f"data/archive/{fpath.name}",
                    )
                )
            except Exception as exc:
                logger.warning("Failed indexing archive %s: %s", fpath.name, exc)

    return HistoryIndex(updated_at=updated_at, weeks=entries[:52])


def _select_spotify_urls_for_enrichment(free_data: Dict[str, Any], limit: int = 24) -> List[str]:
    """Select fastest-rising + top-charting Spotify track URLs for cumulative play count & release date lookup."""
    seen: set[str] = set()
    urls: List[str] = []

    weekly = list(free_data.get("spotify_weekly", []))
    daily = list(free_data.get("spotify_daily", []))

    rising = sorted(
        weekly,
        key=lambda r: (
            1 if str(r.get("rank_change") or "").upper() == "NEW" else 0,
            float(r.get("weekly_growth_pct") or 0.0),
        ),
        reverse=True,
    )
    for row in [*rising[:16], *weekly[:10], *daily[:10]]:
        u = str(row.get("spotify_url") or "").strip()
        if "/track/" in u and u not in seen:
            seen.add(u)
            urls.append(u)
            if len(urls) >= limit:
                break
    return urls


async def run_collection(
    mode: Literal["free", "full"] = "free",
    apify_token: Optional[str] = None,
    max_apify_usd: float = 1.05,
    max_songs_kept: int = 180,
    enrich_limit: int = 420,
    skip_enrichment: bool = False,
    output_dir: Optional[Path] = None,
    cache_path: Optional[Path] = DEFAULT_CACHE_PATH,
) -> WeeklySnapshot:
    """Execute weekly trend collection, enrich previews/covers, score, and persist static JSON files."""
    load_dotenv(ROOT_DIR / ".env")
    out_dir = output_dir or DEFAULT_PUBLIC_DATA_DIR
    archive_dir = out_dir / "archive"
    out_dir.mkdir(parents=True, exist_ok=True)
    archive_dir.mkdir(parents=True, exist_ok=True)

    now_utc = datetime.now(timezone.utc)
    week_id = now_utc.strftime("%Y-%m-%d")
    generated_at = now_utc.isoformat()

    free_data = await fetch_all_free_sources(chart_limit=200)
    if mode == "full":
        apify_client = ApifyCollectorClient(token=apify_token)
        spotify_track_urls = _select_spotify_urls_for_enrichment(free_data, limit=24)
        try:
            apify_data = await apify_client.fetch_all_apify_trends(
                max_budget_usd=max_apify_usd,
                spotify_track_urls=spotify_track_urls,
            )
        except Exception as exc:
            logger.warning("Apify collection failed unexpectedly; falling back to free sources: %s", exc)
            err_msg = f"Error inesperado en Apify ({type(exc).__name__}): {str(exc)[:90]}. Se guardó la actualización gratuita."
            apify_data = {
                "history_songs": [],
                "explore_songs": [],
                "reels_songs": [],
                "shazam_songs": [],
                "spotify_extra_songs": [],
                "statuses": [
                    SourceStatus(
                        id="tiktok_growth_history",
                        name="TikTok 7D Crecimiento Multi-País (Apify)",
                        kind="apify",
                        status="error",
                        note=err_msg,
                    ),
                    SourceStatus(
                        id="tiktok_explore_sounds",
                        name="TikTok Explore 4 Mercados US/GB/MX/ES (Apify)",
                        kind="apify",
                        status="error",
                        note=err_msg,
                    ),
                    SourceStatus(
                        id="instagram_reels_audio",
                        name="Instagram Reels Audio 7D (Apify)",
                        kind="apify",
                        status="error",
                        note=err_msg,
                    ),
                    SourceStatus(
                        id="shazam_global_charts",
                        name="Shazam Top 200 & Viral 50 Global (Apify)",
                        kind="apify",
                        status="error",
                        note=err_msg,
                    ),
                    SourceStatus(
                        id="spotify_viral_plays",
                        name="Spotify Viral 50 + Reproducciones Totales (Apify)",
                        kind="apify",
                        status="error",
                        note=err_msg,
                    ),
                ],
                "total_cost_usd": 0.0,
            }
    else:
        apify_data = {
            "history_songs": [],
            "explore_songs": [],
            "reels_songs": [],
            "shazam_songs": [],
            "spotify_extra_songs": [],
            "statuses": [
                SourceStatus(
                    id="tiktok_growth_history",
                    name="TikTok 7D Crecimiento Multi-País (Apify)",
                    kind="apify",
                    status="skipped",
                    note="Fuente de pago no incluida en modo gratuito.",
                ),
                SourceStatus(
                    id="tiktok_explore_sounds",
                    name="TikTok Explore 4 Mercados US/GB/MX/ES (Apify)",
                    kind="apify",
                    status="skipped",
                    note="Fuente de pago no incluida en modo gratuito.",
                ),
                SourceStatus(
                    id="instagram_reels_audio",
                    name="Instagram Reels Audio 7D (Apify)",
                    kind="apify",
                    status="skipped",
                    note="Fuente de pago no incluida en modo gratuito.",
                ),
                SourceStatus(
                    id="shazam_global_charts",
                    name="Shazam Top 200 & Viral 50 Global (Apify)",
                    kind="apify",
                    status="skipped",
                    note="Fuente de pago no incluida en modo gratuito.",
                ),
                SourceStatus(
                    id="spotify_viral_plays",
                    name="Spotify Viral 50 + Reproducciones Totales (Apify)",
                    kind="apify",
                    status="skipped",
                    note="Fuente de pago no incluida en modo gratuito.",
                ),
            ],
            "total_cost_usd": 0.0,
        }

    merged_dicts = merge_all_sources(free_data, apify_data, updated_at=generated_at)

    # Guarantee high-velocity breakout & social/viral songs aren't pruned before enrichment
    top_by_volume = merged_dicts[:max_songs_kept]
    kept_keys = {s["song_key"] for s in top_by_volume}
    extra_rising = [
        s
        for s in sorted(merged_dicts, key=lambda x: x["velocity_score"], reverse=True)[:50]
        if s["song_key"] not in kept_keys
    ]
    kept_dicts = top_by_volume + extra_rising
    kept_keys = {s["song_key"] for s in kept_dicts}
    extra_social_viral = [
        s
        for s in merged_dicts
        if s["song_key"] not in kept_keys
        and (
            "TikTok" in s.get("platforms", [])
            or "Reels" in s.get("platforms", [])
            or s.get("spotify_viral_rank") is not None
            or s.get("shazam_viral_rank") is not None
        )
    ]
    kept_dicts.extend(extra_social_viral)

    if not skip_enrichment:
        await enrich_songs_metadata(kept_dicts, max_enrich=enrich_limit, cache_path=cache_path)

    songs = [WeeklySongTrend.model_validate(item) for item in kept_dicts]
    prev_snapshot = _load_previous_snapshot(archive_dir, week_id)
    songs = assign_ranks_and_wow(songs, prev_snapshot)

    by_growth = sorted(songs, key=lambda s: (s.velocity_score, s.trend_score), reverse=True)
    tiktok_songs = [s for s in songs if "TikTok" in s.platforms]
    reels_songs = [s for s in songs if "Reels" in s.platforms]
    shazam_viral_songs = [s for s in songs if s.shazam_viral_rank is not None]
    spotify_viral_songs = [s for s in songs if s.spotify_viral_rank is not None]
    social_songs = [s for s in songs if ("TikTok" in s.platforms or "Reels" in s.platforms)]
    social_top = sorted(
        social_songs,
        key=lambda s: (
            max(s.tiktok_7d_growth_pct or 0.0, s.reels_7d_growth_pct or 0.0),
            s.velocity_score,
            s.tiktok_explore_plays or 0,
        ),
        reverse=True,
    )

    statuses = [
        SourceStatus.model_validate(s) if isinstance(s, dict) else s
        for s in (free_data.get("statuses", []) + apify_data.get("statuses", []))
    ]

    summary = SnapshotSummary(
        total_songs=len(songs),
        songs_with_preview=sum(1 for s in songs if bool(s.preview_url or s.youtube_video_id)),
        tiktok_songs_count=len(tiktok_songs),
        reels_songs_count=len(reels_songs),
        shazam_viral_count=len(shazam_viral_songs),
        spotify_viral_count=len(spotify_viral_songs),
        new_entries_count=sum(1 for s in songs if s.is_new_entry),
        multi_platform_count=sum(1 for s in songs if s.platform_count >= 3),
        free_sources_ok=sum(1 for st in statuses if st.kind == "free" and st.status == "ok"),
        apify_sources_ok=sum(1 for st in statuses if st.kind == "apify" and st.status == "ok"),
        total_cost_usd=round(float(apify_data.get("total_cost_usd") or 0.0), 4),
        top_streamed_key=songs[0].song_key if songs else "",
        fastest_growth_key=by_growth[0].song_key if by_growth else "",
        top_social_key=social_top[0].song_key if social_top else "",
    )

    snapshot = WeeklySnapshot(
        week_id=week_id,
        generated_at=generated_at,
        mode=mode,
        summary=summary,
        sources=statuses,
        songs=songs,
    )

    public_snap = snapshot.model_dump()
    if isinstance(public_snap.get("summary"), dict):
        public_snap["summary"].pop("total_cost_usd", None)
    for src in public_snap.get("sources", []):
        if isinstance(src, dict):
            src.pop("cost_usd", None)

    serialized = json.dumps(public_snap, ensure_ascii=False, indent=2)
    (out_dir / "latest.json").write_text(serialized, encoding="utf-8")
    (archive_dir / f"{week_id}.json").write_text(serialized, encoding="utf-8")

    history = _rebuild_history_index(archive_dir, generated_at)
    public_history = history.model_dump()
    for wk in public_history.get("weeks", []):
        if isinstance(wk, dict):
            wk.pop("total_cost_usd", None)
    (out_dir / "history.json").write_text(
        json.dumps(public_history, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return snapshot


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="TrendPulse weekly song trend collector")
    parser.add_argument("--mode", choices=("free", "full"), default="free")
    parser.add_argument("--max-budget", type=float, default=1.05)
    parser.add_argument("--max-songs", type=int, default=180)
    parser.add_argument("--enrich-limit", type=int, default=420)
    parser.add_argument("--skip-enrichment", action="store_true")
    args = parser.parse_args()

    max_budget = float(os.environ.get("APIFY_MAX_CHARGE_PER_RUN_USD", args.max_budget))
    snap = asyncio.run(
        run_collection(
            mode=args.mode,
            max_apify_usd=max_budget,
            max_songs_kept=args.max_songs,
            enrich_limit=args.enrich_limit,
            skip_enrichment=args.skip_enrichment,
        )
    )
    print(
        f"[TrendPulse] week={snap.week_id} mode={snap.mode} "
        f"songs={snap.summary.total_songs} previews={snap.summary.songs_with_preview} "
        f"tiktok={snap.summary.tiktok_songs_count} apify_ok={snap.summary.apify_sources_ok}/5"
    )


if __name__ == "__main__":
    main()
